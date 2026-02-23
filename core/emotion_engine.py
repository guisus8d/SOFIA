# core/emotion_engine.py
# ============================================================
# SocialBot v0.6.3
# FIX 1: Delta máximo de confianza/energía por mensaje = 3.0
#         Evita que un solo "te quiero" suba 15 puntos.
# FIX 2: Umbrales de emoción más realistas + estados intermedios
#         Antes: happy requería e>80 AND t>70 (casi imposible)
#         Ahora: hay 5 zonas más naturales
# ============================================================

from typing import Optional
from models.state import EmotionalState, Emotion
from models.interaction import Interaction
from core.memory import Memory
from utils.logger import logger
from config import settings
import time

MAX_DELTA_PER_MESSAGE = 3.0   # tope de cambio por mensaje (energy y trust)


class EmotionEngine:
    """Gestiona estados emocionales (global o por usuario)"""

    def __init__(self, initial_state: Optional[EmotionalState] = None):
        self.state = initial_state or EmotionalState()
        self.mood_decay = 0.95
        self.last_update_time = time.time()

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
            # Agresión: impacto directo sin tapear (los golpes deben sentirse)
            state.energy = self._clamp(state.energy + aggression_impact.get("energy", 0))
            state.trust  = self._clamp(state.trust  + aggression_impact.get("trust",  0))

        else:
            # Flujo normal — calcular delta y tapearlo
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

            energy_delta = total_impact * 0.3
            trust_delta  = total_impact * 0.2

            state.energy = self._clamp(state.energy + self._cap_delta(energy_delta))
            state.trust  = self._clamp(state.trust  + self._cap_delta(trust_delta))

        self._update_primary_emotion(state)
        state.last_updated = interaction.timestamp.timestamp()
        return state

    # ==========================================================
    # LÓGICA INTERNA
    # ==========================================================

    def _cap_delta(self, delta: float) -> float:
        """Limita el cambio máximo por mensaje para subidas/bajadas graduales."""
        return max(-MAX_DELTA_PER_MESSAGE, min(MAX_DELTA_PER_MESSAGE, delta))

    def _apply_time_decay_to_state(self, state: EmotionalState, reference_time: float):
        if not state.last_updated:
            return
        hours_passed = (reference_time - state.last_updated) / 3600
        if hours_passed <= 0:
            return
        decay_factor = self.mood_decay ** hours_passed
        state.energy = self._clamp(state.energy * decay_factor)
        state.trust  = self._clamp(state.trust  * decay_factor)

    def _update_primary_emotion(self, state: EmotionalState):
        """
        FIX v0.6.3: Umbrales más realistas.

        Zonas:
          happy   → e > 65 AND t > 60   (alcanzable con conversación positiva)
          sad     → e < 25              (energía muy baja)
          angry   → t < 25              (confianza muy baja)
          fearful → e < 40 AND t < 40   (ambas bajas)
          neutral → todo lo demás
        """
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