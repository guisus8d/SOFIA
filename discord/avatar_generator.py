# discord/avatar_generator.py
# ============================================================
# AvatarGenerator — genera avatares via Pollinations.ai
# v2 — descarga la imagen y la manda como archivo Discord
# ============================================================

from __future__ import annotations

import hashlib
import io
import logging
import re
import urllib.parse
from typing import Optional, Tuple

import aiohttp

logger = logging.getLogger("sofia_avatar")

_STYLE_MAP = {
    "happy":   "vibrant anime style, warm colors, glowing eyes, cherry blossoms, soft glow",
    "sad":     "melancholic anime style, cool blue tones, rain, soft lighting, introspective",
    "angry":   "dark anime style, dramatic shadows, intense expression, red accents",
    "fearful": "ethereal anime style, moonlight, mysterious atmosphere, soft purple haze",
    "neutral": "clean anime style, balanced colors, calm expression, cinematic lighting",
}

_TOPIC_ELEMENTS = {
    "música":     "musical notes floating, headphones, sound waves",
    "anime":      "sakura petals, japanese aesthetic, vibrant colors",
    "gaming":     "holographic hud elements, pixel accents, neon glow",
    "arte":       "paintbrush strokes background, colorful palette",
    "tecnología": "circuit patterns, holographic interface, cyberpunk accents",
    "deportes":   "dynamic motion blur, energy lines",
    "naturaleza": "forest elements, flowers, soft natural lighting",
    "memes":      "playful cartoon elements, bright fun colors",
}


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
                f"{subject.strip()} character, anime style, high quality portrait, "
                f"detailed illustration, solo character, centered composition, "
                f"masterpiece quality, dramatic lighting, vivid colors"
            )

        # Basado en perfil del usuario
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
                warmth = "cool distant lighting, reserved expression"

        name_clean = re.sub(r'[^a-zA-Z\s]', '', display_name).strip() or "character"
        topic_str  = ", ".join(topic_extras) if topic_extras else "bokeh background"

        return (
            f"portrait of anime character representing {name_clean}, "
            f"{style}, {topic_str}, {warmth}, "
            f"high detail, professional illustration, solo character, "
            f"centered composition, masterpiece quality"
        )

    def _build_url(self, prompt: str, seed: int = 42) -> str:
        encoded = urllib.parse.quote(prompt)
        return (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=512&height=512&seed={seed}&nologo=true&enhance=true&model=flux"
        )

    def _seed(self, user_id: str) -> int:
        return int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16) % 100000

    async def fetch_image(
        self,
        user_id: str,
        display_name: str,
        profile=None,
        subject: Optional[str] = None,
    ) -> Tuple[Optional[io.BytesIO], str]:
        """
        Descarga la imagen y retorna (BytesIO, filename).
        Retorna (None, "") si falla.
        """
        prompt = self._build_prompt(display_name, profile, subject)
        url    = self._build_url(prompt, self._seed(user_id))

        logger.info(f"Generando avatar | {display_name} | subject={subject}")

        try:
            # Pollinations puede tardar hasta 90s generando — es normal
            connector = aiohttp.TCPConnector(limit=5)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=90, connect=15),
                    headers={"User-Agent": "SofiaBot/1.0"},
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Pollinations {resp.status}")
                        return None, ""

                    data = await resp.read()
                    if len(data) < 1000:
                        logger.warning(f"Imagen inválida ({len(data)}b)")
                        return None, ""

                    return io.BytesIO(data), f"avatar_{user_id[:8]}.png"

        except asyncio.TimeoutError:
            logger.warning("Pollinations tardó demasiado (>90s)")
            return None, ""
        except Exception as e:
            logger.error(f"Error descargando avatar: {e}")
            return None, ""