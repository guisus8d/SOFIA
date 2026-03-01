# discord/avatar_generator.py
# ============================================================
# AvatarGenerator — genera avatares personalizados via Pollinations.ai
# Sin API key. Gratis. Basado en la personalidad real del usuario.
# ============================================================

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import urllib.parse
from typing import Optional

import aiohttp

logger = logging.getLogger("sofia_avatar")

# Base URL de Pollinations
_POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"

# Estilos artísticos disponibles — se selecciona según personalidad
_STYLE_MAP = {
    "happy":   "vibrant anime style, warm colors, glowing eyes, cherry blossoms",
    "sad":     "melancholic anime style, cool blue tones, rain, soft lighting",
    "angry":   "dark anime style, dramatic shadows, intense expression, red accents",
    "fearful": "ethereal anime style, moonlight, mysterious atmosphere, soft purple",
    "neutral": "clean anime style, balanced colors, calm expression, cinematic lighting",
}

# Elementos visuales por temas de interés
_TOPIC_ELEMENTS = {
    "música":     "musical notes floating, headphones, sound waves",
    "anime":      "anime aesthetic, sakura petals, japanese elements",
    "gaming":     "holographic hud elements, pixel accents, neon glow",
    "arte":       "paintbrush strokes background, colorful palette, artistic flair",
    "tecnología": "circuit patterns, holographic interface, cyberpunk accents",
    "deportes":   "dynamic motion blur, energy lines, athletic vibe",
    "naturaleza": "forest elements, flowers, soft natural lighting",
    "música":     "vinyl records, microphone, stage lighting",
    "memes":      "playful cartoon elements, bright colors, fun expression",
    "trabajo":    "professional aesthetic, clean lines, modern style",
}


class AvatarGenerator:

    def __init__(self):
        self.base_url = _POLLINATIONS_URL

    async def generate_for_user(
        self,
        user_id: str,
        display_name: str,
        profile=None,
    ) -> Optional[str]:
        """
        Genera una URL de avatar personalizado basado en el perfil del usuario.
        Retorna la URL de la imagen lista para enviar a Discord.
        """
        prompt = self._build_prompt(user_id, display_name, profile)
        url    = self._build_url(prompt, seed=self._name_seed(user_id))
        logger.info(f"Avatar generado para {display_name}: {url[:80]}...")
        return url

    def _build_prompt(
        self,
        user_id: str,
        display_name: str,
        profile=None,
    ) -> str:
        """
        Construye un prompt de imagen basado en la personalidad real del usuario.
        """
        # Emoción base del perfil
        emotion = "neutral"
        if profile and hasattr(profile, "emotional_state") and profile.emotional_state:
            emotion = profile.emotional_state.primary_emotion.value

        style = _STYLE_MAP.get(emotion, _STYLE_MAP["neutral"])

        # Elementos según temas de interés
        topic_extras = []
        if profile and hasattr(profile, "topics") and profile.topics:
            for topic in profile.topics[:3]:
                t = topic.lower().strip()
                for key, element in _TOPIC_ELEMENTS.items():
                    if key in t:
                        topic_extras.append(element)
                        break

        # Nivel de confianza → calidez del diseño
        warmth = "warm soft glow"
        if profile and hasattr(profile, "emotional_state") and profile.emotional_state:
            trust = profile.emotional_state.trust
            if trust > 70:
                warmth = "warm golden light, friendly aura"
            elif trust < 30:
                warmth = "cool distant lighting, reserved expression"

        # Construir prompt final
        topic_str = ", ".join(topic_extras[:2]) if topic_extras else "bokeh background"
        name_clean = re.sub(r'[^a-zA-Z\s]', '', display_name).strip() or "character"

        prompt = (
            f"portrait of an anime character representing {name_clean}, "
            f"{style}, {topic_str}, {warmth}, "
            f"high detail, professional illustration, solo character, "
            f"centered composition, 512x512, masterpiece quality"
        )

        return prompt

    def _build_url(self, prompt: str, seed: int = 42) -> str:
        encoded = urllib.parse.quote(prompt)
        return (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=512&height=512&seed={seed}&nologo=true&enhance=true"
        )

    def _name_seed(self, user_id: str) -> int:
        """Seed consistente por usuario — el mismo user siempre obtiene el mismo avatar base."""
        return int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16) % 100000

    async def preload(self, url: str) -> bool:
        """
        Hace una petición HEAD para que Pollinations pre-genere la imagen
        antes de que Discord intente cargarla.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as r:
                    return r.status == 200
        except Exception as e:
            logger.warning(f"Preload fallido: {e}")
            return False