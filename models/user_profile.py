from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
from models.state import EmotionalState
from core.personality_core import PERSONALITY_CORE

RELATIONAL_TRAIT_KEYS = list(PERSONALITY_CORE.keys())

@dataclass
class UserProfile:
    user_id: str
    emotional_state: EmotionalState = field(default_factory=EmotionalState)
    interaction_count: int = 0
    communication_style: str = "neutral"
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    topics: List[str] = field(default_factory=list)
    
    # 🔄 OFFSETS: desviación respecto al núcleo
    personality_offsets: Dict[str, float] = field(
        default_factory=lambda: {k: 0.0 for k in RELATIONAL_TRAIT_KEYS}
    )
    
    # 🧠 Hechos importantes (memoria selectiva)
    important_facts: Dict[str, float] = field(default_factory=dict)

    # ⚠️ NUEVO: Daño relacional acumulado (0 = sin daño, >0 = daño)
    relationship_damage: float = 0.0

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "emotional_state": self.emotional_state.to_dict() if self.emotional_state else None,
            "interaction_count": self.interaction_count,
            "communication_style": self.communication_style,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "topics": self.topics,
            "personality_offsets": self.personality_offsets,
            "important_facts": self.important_facts,
            "relationship_damage": self.relationship_damage   # ← nuevo campo
        }

    @classmethod
    def from_dict(cls, data: dict):
        emotional_state_data = data.get("emotional_state")
        emotional_state = EmotionalState.from_dict(emotional_state_data) if emotional_state_data else EmotionalState()

        topics = data.get("topics", [])
        if isinstance(topics, str):
            topics = [t.strip() for t in topics.split(",") if t.strip()]

        # Migración desde personality_traits si existe
        old_traits = data.get("personality_traits")
        if old_traits is not None:
            offsets = {}
            for k in RELATIONAL_TRAIT_KEYS:
                old_val = old_traits.get(k, PERSONALITY_CORE[k])
                offsets[k] = old_val - PERSONALITY_CORE[k]
        else:
            offsets = data.get("personality_offsets", {})
            offsets = {k: offsets.get(k, 0.0) for k in RELATIONAL_TRAIT_KEYS}

        important_facts = data.get("important_facts") or {}
        if not isinstance(important_facts, dict):
            important_facts = {}

        # Cargar relationship_damage (si no existe, inicializar a 0)
        relationship_damage = data.get("relationship_damage", 0.0)

        return cls(
            user_id=data["user_id"],
            emotional_state=emotional_state,
            interaction_count=data.get("interaction_count", 0),
            communication_style=data.get("communication_style", "neutral"),
            first_seen=datetime.fromisoformat(data["first_seen"]) if data.get("first_seen") else None,
            last_seen=datetime.fromisoformat(data["last_seen"]) if data.get("last_seen") else None,
            topics=topics,
            personality_offsets=offsets,
            important_facts=important_facts,
            relationship_damage=relationship_damage
        )