# models/state.py
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class Emotion(Enum):
    HAPPY = "happy"
    NEUTRAL = "neutral"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"

@dataclass
class EmotionalState:
    """Estado emocional actual del bot"""
    primary_emotion: Emotion = Emotion.NEUTRAL
    energy: float = 100.0      # 0-100, qué tan activo/enérgico
    trust: float = 100.0       # 0-100, confianza general en usuarios
    last_updated: Optional[float] = None  # timestamp

    def to_dict(self) -> dict:
        return {
            "emotion": self.primary_emotion.value,
            "energy": self.energy,
            "trust": self.trust,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            primary_emotion=Emotion(data.get("emotion", "neutral")),
            energy=data.get("energy", 50.0),
            trust=data.get("trust", 50.0),
            last_updated=data.get("last_updated")
        )