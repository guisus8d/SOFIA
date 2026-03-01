# discord/avatar_generator.py
# ============================================================
# AvatarGenerator — Hugging Face Inference API
# Modelo: animagine-xl-3.1 (anime de alta calidad, gratis con HF token)
# Fallback: Pollinations.ai si HF falla
# ============================================================

from __future__ import annotations

import hashlib
import io
import logging
import os
import re
import urllib.parse
from typing import Optional, Tuple

import aiohttp

logger = logging.getLogger("sofia_avatar")

# Modelo anime de alta calidad en HF
_HF_MODEL   = "cagliostrolab/animagine-xl-3.1"
_HF_API_URL = f"https://api-inference.huggingface.co/models/{_HF_MODEL}"
_HF_TOKEN   = os.environ.get("HF_TOKEN", "")

_STYLE_MAP = {
    "happy":   "vibrant, warm colors, glowing eyes, cherry blossoms, soft smile, cheerful expression",
    "sad":     "cool blue tones, melancholic expression, rain, soft lighting, introspective look",
    "angry":   "dramatic shadows, intense expression, red accents, fierce look",
    "fearful": "moonlight, mysterious atmosphere, soft purple haze, wide eyes",
    "neutral": "balanced colors, calm expression, cinematic lighting, serene look",
}

_TOPIC_ELEMENTS = {
    "música":     "headphones, musical notes floating, stage lighting",
    "anime":      "sakura petals, japanese aesthetic, vibrant colors",
    "gaming":     "holographic hud, neon glow, pixel accents",
    "arte":       "paintbrush strokes background, colorful palette",
    "tecnología": "circuit patterns, cyberpunk accents, holographic interface",
    "deportes":   "dynamic motion blur, energy lines",
    "naturaleza": "flowers, forest background, soft natural lighting",
    "memes":      "playful expression, bright colors",
}

# Negative prompt estándar para anime de calidad
_NEGATIVE = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, "
    "extra digit, fewer digits, cropped, worst quality, low quality, "
    "normal quality, jpeg artifacts, signature, watermark, username, blurry"
)


class AvatarGenerator:

    def _build_prompt(
        self,
        display_name: str,
        profile=None,
        subject: Optional[str] = None,
    ) -> str:

        # Personaje/estilo específico pedido por el usuario
        if subject:
            return (
                f"{subject.strip()}, anime style, high quality, detailed, "
                f"solo character, centered composition, masterpiece, best quality, "
                f"dramatic lighting, vivid colors, 1girl or 1boy"
            )

        # Basado en perfil
        emotion = "neutral"
        if profile and hasattr(profile, "emotional_state") and profile.emotional_state:
            emotion = profile.emotional_state.primary_emotion.value

        style = _STYLE_MAP.get(emotion, _STYLE_MAP["neutral"])

        topic_extras = []
        if profile and hasattr(profile, "topics") and profile.topics:
            for topic in profile.topics[:2]:
                t = topic.lower().strip()
                for key, element in _TOPIC_ELEMENTS.items():
                    if key in t:
                        topic_extras.append(element)
                        break

        warmth = "warm soft glow"
        if profile and hasattr(profile, "emotional_state") and profile.emotional_state:
            trust = profile.emotional_state.trust
            if trust > 70:
                warmth = "warm golden light, friendly aura"
            elif trust < 30:
                warmth = "cool distant lighting"

        name_clean = re.sub(r'[^a-zA-Z\s]', '', display_name).strip() or "character"
        topic_str  = ", ".join(topic_extras) if topic_extras else "bokeh background"

        return (
            f"anime portrait of a character named {name_clean}, "
            f"{style}, {topic_str}, {warmth}, "
            f"high detail, masterpiece, best quality, solo, "
            f"centered composition, professional illustration"
        )

    def _seed(self, user_id: str) -> int:
        return int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16) % 2147483647

    async def fetch_image(
        self,
        user_id: str,
        display_name: str,
        profile=None,
        subject: Optional[str] = None,
    ) -> Tuple[Optional[io.BytesIO], str]:

        prompt = self._build_prompt(display_name, profile, subject)
        logger.info(f"Generando imagen | {display_name} | subject={subject}")

        # Intentar HF primero
        if _HF_TOKEN:
            result = await self._fetch_hf(prompt, user_id)
            if result[0]:
                return result

        # Fallback a Pollinations
        logger.warning("HF falló o sin token — intentando Pollinations")
        return await self._fetch_pollinations(prompt, user_id)

    async def _fetch_hf(
        self, prompt: str, user_id: str
    ) -> Tuple[Optional[io.BytesIO], str]:

        payload = {
            "inputs": prompt,
            "parameters": {
                "negative_prompt": _NEGATIVE,
                "num_inference_steps": 28,
                "guidance_scale": 7.0,
                "width": 512,
                "height": 512,
                "seed": self._seed(user_id),
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    _HF_API_URL,
                    headers={
                        "Authorization": f"Bearer {_HF_TOKEN}",
                        "Content-Type":  "application/json",
                    },
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=90),
                ) as resp:

                    if resp.status == 503:
                        # Modelo cargando — esperar y reintentar una vez
                        logger.info("HF modelo cargando (503), reintentando en 20s...")
                        import asyncio
                        await asyncio.sleep(20)
                        return await self._fetch_hf(prompt, user_id)

                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning(f"HF error {resp.status}: {body[:200]}")
                        return None, ""

                    data = await resp.read()
                    if len(data) < 1000:
                        logger.warning(f"HF imagen muy pequeña ({len(data)}b)")
                        return None, ""

                    return io.BytesIO(data), f"avatar_{user_id[:8]}.png"

        except Exception as e:
            logger.error(f"HF fetch error: {e}")
            return None, ""

    async def _fetch_pollinations(
        self, prompt: str, user_id: str
    ) -> Tuple[Optional[io.BytesIO], str]:

        encoded = urllib.parse.quote(prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=512&height=512&seed={self._seed(user_id)}&nologo=true"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=60),
                    headers={"User-Agent": "SofiaBot/1.0"},
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Pollinations {resp.status}")
                        return None, ""

                    data = await resp.read()
                    if len(data) < 1000:
                        return None, ""

                    return io.BytesIO(data), f"avatar_{user_id[:8]}.png"

        except Exception as e:
            logger.error(f"Pollinations error: {e}")
            return None, ""