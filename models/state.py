# models/state.py
# ============================================================
# SocialBot v0.12.0
# CAMBIOS vs v0.8.x:
#   - EmotionalState extendido con tone, initiative, verbosity
#   - Campos nuevos tienen defaults — retrocompatible al 100%
#   - to_dict / from_dict actualizados
# ============================================================

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Literal


class Emotion(Enum):
    HAPPY   = "happy"
    NEUTRAL = "neutral"
    SAD     = "sad"
    ANGRY   = "angry"
    FEARFUL = "fearful"


# ── Tipos de expression hints ─────────────────────────────

ToneType       = Literal["warm", "playful", "neutral", "slightly_cold", "cold"]
InitiativeType = Literal["high", "medium", "low"]
VerbosityType  = Literal["verbose", "medium", "brief"]


@dataclass
class EmotionalState:
    """
    Estado emocional actual del bot.

    Campos base (existían antes):
        primary_emotion, energy, trust, last_updated

    Campos nuevos (v0.12.0) — expression hints:
        tone        → cómo suena la respuesta
        initiative  → cuánto toma iniciativa
        verbosity   → qué tan larga es la respuesta

    Los campos nuevos son derivados por EmotionRegistry._derive_expression_hints()
    y consumidos por sofia_voice.py para elegir entre variantes.
    Nunca se usan en lógica de decisión — solo en expresión.
    """

    # ── Campos base ──────────────────────────────────────────
    primary_emotion: Emotion = Emotion.NEUTRAL
    energy: float  = 50.0   # 0–100
    trust:  float  = 50.0   # 0–100
    last_updated: Optional[float] = None  # unix timestamp

    # ── Expression hints (nuevos, con defaults seguros) ──────
    tone:       ToneType       = "neutral"
    initiative: InitiativeType = "medium"
    verbosity:  VerbosityType  = "medium"

    # ── Serialización ────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "emotion":      self.primary_emotion.value,
            "energy":       self.energy,
            "trust":        self.trust,
            "last_updated": self.last_updated,
            # nuevos — opcionales en from_dict para no romper DBs viejas
            "tone":         self.tone,
            "initiative":   self.initiative,
            "verbosity":    self.verbosity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EmotionalState":
        return cls(
            primary_emotion = Emotion(data.get("emotion", "neutral")),
            energy          = data.get("energy", 50.0),
            trust           = data.get("trust",  50.0),
            last_updated    = data.get("last_updated"),
            # nuevos campos — si no existen en la DB vieja, usan defaults
            tone            = data.get("tone",       "neutral"),
            initiative      = data.get("initiative", "medium"),
            verbosity       = data.get("verbosity",  "medium"),
        )

    # ── Helpers de conveniencia ──────────────────────────────

    @property
    def is_distressed(self) -> bool:
        """True si la combinación de emoción/energía indica malestar."""
        return self.primary_emotion in (Emotion.SAD, Emotion.FEARFUL) or self.energy < 30

    @property
    def is_positive(self) -> bool:
        return self.primary_emotion == Emotion.HAPPY and self.energy > 60