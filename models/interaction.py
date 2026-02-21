# models/interaction.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Interaction:
    """Registro de una interacción con un usuario"""
    user_id: str
    message: str
    sentiment: float  # -1 a 1
    response: str
    timestamp: datetime
    emotion_before: str
    emotion_after: str

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "message": self.message,
            "sentiment": self.sentiment,
            "response": self.response,
            "timestamp": self.timestamp.isoformat(),
            "emotion_before": self.emotion_before,
            "emotion_after": self.emotion_after
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            user_id=data["user_id"],
            message=data["message"],
            sentiment=data["sentiment"],
            response=data["response"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            emotion_before=data["emotion_before"],
            emotion_after=data["emotion_after"]
        )