# core/emotion_engine.py
# ============================================================
# SocialBot v0.12.4
# CAMBIOS vs v0.12.0:
#   - FIX Bug VERBOSITY #6: se calcula is_flood via Fatigue.is_char_flood()
#     y se pasa al message_event. El registry ya lo usa para forzar
#     verbosity mínimo "medium" en flood aunque fatigue sea baja.
#   - FIX Bug STRESS_COMBO #8: retractaciones ("era broma", "estoy bien",
#     "no era en serio") con sentiment alto caían a affection_event,
#     generando respuesta afectuosa + jeje inapropiado post-crisis.
#     Ahora se detectan antes del check de sentiment y caen a message_event.
#   - MANTIENE: todo lo demás de v0.12.0 intacto.
# ============================================================

from typing import Optional
from models.state import EmotionalState, Emotion
from models.interaction import Interaction
from core.memory import Memory
from core.emotion.emotion_registry import EmotionRegistry
from core.emotion.event_bus import (
    message_event, aggression_event, repair_event,
    affection_event, time_event,
)
from core.emotion.modules.fatigue import Fatigue
from utils.logger import logger
from config import settings
import time
from datetime import datetime


class EmotionEngine:
    """
    Fachada pública del motor emocional.
    Mantiene la misma API que v0.8.0 para no romper nada.
    Internamente delega toda la lógica al EmotionRegistry modular.
    """

    MOOD_REASONS = {
        "aggression":   "alguien fue grosero conmigo",
        "affection":    "alguien fue muy amable",
        "long_silence": "pasó mucho tiempo sin hablar",
        "good_vibes":   "la conversación estuvo muy buena",
        "repetition":   "siento que la conversación se estancó",
        "recovery":     "estamos arreglando las cosas poco a poco",
    }

    def __init__(self, initial_state: Optional[EmotionalState] = None):
        self.state = initial_state or EmotionalState()
        self.last_update_time = time.time()
        # Registry global (para llamadas sin user_id explícito)
        self._registry = EmotionRegistry()
        # Registry por usuario { user_id: EmotionRegistry }
        self._registries: dict[str, EmotionRegistry] = {}

    # ==========================================================
    # API PÚBLICA — idéntica a v0.8.0
    # ==========================================================

    async def process_interaction(
        self,
        interaction: Interaction,
        memory: Memory,
    ) -> EmotionalState:
        updated = await self.process_interaction_for_state(
            state=self.state,
            interaction=interaction,
            memory=memory,
        )
        self.state = updated
        self.last_update_time = time.time()
        logger.info(
            f"Emoción actualizada: {updated.primary_emotion.value} "
            f"(energía={updated.energy:.1f}, confianza={updated.trust:.1f}, "
            f"tono={updated.tone})"
        )
        return updated

    async def process_interaction_for_state(
        self,
        state: EmotionalState,
        interaction: Interaction,
        memory: Memory,
        repair_multiplier: float = 1.0,
        relationship_damage: float = 0.0,
        aggression_impact: dict = None,
    ) -> EmotionalState:

        registry = self._get_registry(interaction.user_id)
        ts = interaction.timestamp.timestamp()

        # ── 1. Decay por tiempo ──────────────────────────────
        if state.last_updated:
            hours = (ts - state.last_updated) / 3600
            if hours > 0:
                registry.apply_decay(hours, state)

        # ── 2. Construir evento ──────────────────────────────
        msg = getattr(interaction, "message", "")

        # FIX v0.12.4 Bug 1: detectar flood antes de clasificar el evento
        _is_flood = Fatigue.is_char_flood(msg)

        # FIX v0.12.4 Bug 3: retractaciones ("era broma", "estoy bien", etc.)
        # pueden tener sentiment alto y caer a affection_event por error.
        # Se detectan aquí y se fuerzan a message_event para que
        # decision_engine las maneje como retractación, no como afecto.
        _RETRACTION_MARKERS = (
            "era broma", "es broma", "fue broma",
            "estoy bien", "ya estoy bien", "no era en serio",
            "no lo decía en serio", "no fue en serio",
            "solo bromeaba", "solo era broma",
        )
        _is_retraction = any(m in msg.lower() for m in _RETRACTION_MARKERS)

        if aggression_impact:
            # Agresión detectada por AggressionDetector
            agg_score = min(
                abs(aggression_impact.get("energy", -5)) / 15.0,
                1.0
            )
            event = aggression_event(
                user_id=interaction.user_id,
                timestamp=ts,
                aggression_score=agg_score,
                sentiment=interaction.sentiment,
            )

        elif repair_multiplier > 1.0 and interaction.sentiment >= 0:
            # Usuario se está disculpando
            repair_score = min((repair_multiplier - 1.0) / 2.0, 1.0)
            event = repair_event(
                user_id=interaction.user_id,
                timestamp=ts,
                repair_score=repair_score,
                sentiment=interaction.sentiment,
            )

        elif interaction.sentiment > 0.6 and not _is_retraction and not _is_flood:
            # Afecto fuerte — solo si no es retractación ni flood
            event = affection_event(
                user_id=interaction.user_id,
                timestamp=ts,
                affection_score=interaction.sentiment,
                sentiment=interaction.sentiment,
            )

        else:
            # Mensaje normal (incluye retracciones y flood)
            event = message_event(
                user_id=interaction.user_id,
                timestamp=ts,
                sentiment=interaction.sentiment,
                message_len=len(msg),
                is_question="?" in msg,
                is_flood=_is_flood,
            )

        # ── 3. Procesar con el registry ──────────────────────
        registry.process(event, state)

        state.last_updated = ts
        return state

    # ==========================================================
    # MOOD REASON
    # ==========================================================

    def get_mood_reason(self, user_id: str) -> Optional[str]:
        registry = self._registries.get(user_id)
        if not registry:
            return None
        reason_key = registry.last_reason
        return self.MOOD_REASONS.get(reason_key)

    def clear_mood_reason(self, user_id: str):
        registry = self._registries.get(user_id)
        if registry:
            registry._last_reason = ""

    # ==========================================================
    # MODO NOCHE
    # ==========================================================

    def is_night_mode(self) -> bool:
        hour  = datetime.now().hour
        start = settings.NIGHT_MODE_START_HOUR
        end   = settings.NIGHT_MODE_END_HOUR
        if start > end:
            return hour >= start or hour < end
        return start <= hour < end

    # ==========================================================
    # ACCESO A REGISTRY POR USUARIO
    # ==========================================================

    def get_registry(self, user_id: str) -> EmotionRegistry:
        """Acceso directo al registry de un usuario (para debug/admin)."""
        return self._get_registry(user_id)

    def _get_registry(self, user_id: str) -> EmotionRegistry:
        if user_id not in self._registries:
            self._registries[user_id] = EmotionRegistry()
        return self._registries[user_id]