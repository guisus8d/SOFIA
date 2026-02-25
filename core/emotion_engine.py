# core/emotion_engine.py
# ============================================================
# SocialBot v0.8.0
# FIX: Indentación rota del archivo original (emotion_engine estaba
#      accidentalmente anidado dentro de _get_secret).
# NUEVO: mood_reason — Sofía sabe POR QUÉ está en cierto estado.
#        Permite respuestas como "todavía pienso en lo que me dijiste".
# NUEVO: Modo noche — energy_decay más suave de noche, tono más íntimo.
# ============================================================

from typing import Optional
from models.state import EmotionalState, Emotion
from models.interaction import Interaction
from core.memory import Memory
from utils.logger import logger
from config import settings
import time
from datetime import datetime

MAX_DELTA_PER_MESSAGE = 3.0


class EmotionEngine:
    """Gestiona estados emocionales por usuario."""

    # Razones internas que Sofía puede referenciar en sus respuestas
    MOOD_REASONS = {
        "aggression":    "alguien fue grosero conmigo",
        "affection":     "alguien fue muy amable",
        "long_silence":  "pasó mucho tiempo sin hablar",
        "good_vibes":    "la conversación estuvo muy buena",
        "repetition":    "siento que la conversación se estancó",
        "recovery":      "estamos arreglando las cosas poco a poco",
    }

    def __init__(self, initial_state: Optional[EmotionalState] = None):
        self.state = initial_state or EmotionalState()
        self.mood_decay = 0.95
        self.last_update_time = time.time()
        # mood_reason por usuario { user_id: str }
        self._mood_reasons: dict = {}

    # ==========================================================
    # MÉTODO GLOBAL
    # ==========================================================

    async def process_interaction(
        self,
        interaction: Interaction,
        memory: Memory
    ) -> EmotionalState:
        updated = await self.process_interaction_for_state(
            state=self.state,
            interaction=interaction,
            memory=memory
        )
        self.state = updated
        self.last_update_time = time.time()
        logger.info(
            f"Emoción actualizada: {updated.primary_emotion.value} "
            f"(energía={updated.energy:.1f}, confianza={updated.trust:.1f})"
        )
        return updated

    # ==========================================================
    # MÉTODO POR ESTADO EXTERNO
    # ==========================================================

    async def process_interaction_for_state(
        self,
        state: EmotionalState,
        interaction: Interaction,
        memory: Memory,
        repair_multiplier: float = 1.0,
        relationship_damage: float = 0.0,
        aggression_impact: dict = None,
    ) -> EmotionalState:

        self._apply_time_decay_to_state(state, interaction.timestamp.timestamp())

        if aggression_impact:
            state.energy = self._clamp(state.energy + aggression_impact.get("energy", 0))
            state.trust  = self._clamp(state.trust  + aggression_impact.get("trust",  0))
            # Registrar razón del estado
            self._mood_reasons[interaction.user_id] = self.MOOD_REASONS["aggression"]

        else:
            sentiment_impact = interaction.sentiment * 15
            history_impact   = memory.get_average_sentiment_for(interaction.user_id) * 10
            global_impact    = memory.get_recent_global_sentiment() * 5
            total_impact     = sentiment_impact + history_impact + global_impact

            if interaction.sentiment >= 0 and repair_multiplier > 1.0:
                total_impact += settings.REPAIR_ENERGY_BOOST * repair_multiplier
                trust_repair  = settings.REPAIR_TRUST_BOOST * repair_multiplier
                state.trust  = self._clamp(
                    state.trust + self._cap_delta(trust_repair)
                )
                self._mood_reasons[interaction.user_id] = self.MOOD_REASONS["recovery"]

            elif interaction.sentiment > 0.6:
                self._mood_reasons[interaction.user_id] = self.MOOD_REASONS["affection"]
            elif interaction.sentiment > 0.3:
                self._mood_reasons[interaction.user_id] = self.MOOD_REASONS["good_vibes"]

            energy_delta = total_impact * 0.3
            trust_delta  = total_impact * 0.2

            state.energy = self._clamp(state.energy + self._cap_delta(energy_delta))
            state.trust  = self._clamp(state.trust  + self._cap_delta(trust_delta))

        self._update_primary_emotion(state)
        state.last_updated = interaction.timestamp.timestamp()
        return state

    # ==========================================================
    # MOOD REASON — para que Sofía referencie su estado
    # ==========================================================

    def get_mood_reason(self, user_id: str) -> Optional[str]:
        """Retorna la razón del estado emocional actual (o None)."""
        return self._mood_reasons.get(user_id)

    def clear_mood_reason(self, user_id: str):
        self._mood_reasons.pop(user_id, None)

    # ==========================================================
    # MODO NOCHE
    # ==========================================================

    def is_night_mode(self) -> bool:
        """Retorna True si la hora actual está en modo noche."""
        hour = datetime.now().hour
        start = settings.NIGHT_MODE_START_HOUR
        end   = settings.NIGHT_MODE_END_HOUR
        # Maneja el cruce de medianoche (ej: 22-6)
        if start > end:
            return hour >= start or hour < end
        return start <= hour < end

    # ==========================================================
    # LÓGICA INTERNA
    # ==========================================================

    def _cap_delta(self, delta: float) -> float:
        return max(-MAX_DELTA_PER_MESSAGE, min(MAX_DELTA_PER_MESSAGE, delta))

    def _apply_time_decay_to_state(self, state: EmotionalState, reference_time: float):
        if not state.last_updated:
            return
        hours_passed = (reference_time - state.last_updated) / 3600
        if hours_passed <= 0:
            return
        decay_factor = self.mood_decay ** hours_passed
        # FIX BUG 12: el decay solo afecta energía (estado de ánimo del momento),
        # no la confianza (relación construida). Un usuario que no habla por días
        # no debería recibir respuestas hostiles porque su trust llegó a 0.
        state.energy = self._clamp(state.energy * decay_factor)
        # trust decae mucho más lentamente: 1% por hora en vez del 5%
        slow_trust_decay = 0.99 ** hours_passed
        state.trust  = self._clamp(state.trust * slow_trust_decay)

    def _update_primary_emotion(self, state: EmotionalState):
        e = state.energy
        t = state.trust

        if e > 65 and t > 60:
            state.primary_emotion = Emotion.HAPPY
        elif e < 25:
            state.primary_emotion = Emotion.SAD
        elif t < 25:
            state.primary_emotion = Emotion.ANGRY
        elif e < 40 and t < 40:
            state.primary_emotion = Emotion.FEARFUL
        else:
            state.primary_emotion = Emotion.NEUTRAL

    def _clamp(self, value: float) -> float:
        return max(0.0, min(100.0, value))