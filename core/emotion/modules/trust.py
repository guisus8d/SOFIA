# core/emotion/modules/trust.py
# ============================================================
# Módulo: Trust
# Representa la confianza acumulada en la relación.
# Sube lento, baja rápido con traición/agresión.
# Es el módulo con más peso en decisiones de apertura.
# Decay muy lento — la confianza es relacional, no del momento.
# ============================================================

from typing import Optional
from core.emotion.base_emotion import BaseEmotion, EmotionSignal
from core.emotion.event_bus import EmotionEvent, EventType


class Trust(BaseEmotion):
    name = "trust"
    INITIAL_VALUE = 50.0

    # ── Constantes deterministas ────────────────────────────
    _AFFECTION_GAIN     =  8.0
    _REPAIR_GAIN        =  6.0
    _POSITIVE_MSG_GAIN  =  1.5    # mensajes positivos acumulan confianza lento
    _AGGRESSION_LOSS    = -18.0   # agresión destruye confianza rápido
    _COLD_MSG_LOSS      = -0.5    # mensajes fríos sostenidos la erosionan
    _DECAY_RATE         =  0.998  # decay muy lento (relación construida)

    # Niveles de trust
    _LEVEL_HIGH         =  70.0
    _LEVEL_MID          =  40.0

    def on_event(self, event: EmotionEvent) -> Optional[EmotionSignal]:
        if event.type == EventType.AFFECTION:
            delta = self._AFFECTION_GAIN * event.affection_score
            self._apply_delta(delta)
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=+4.0,
                trust_delta=delta,
                priority=1,
                reason="affection",
            )

        if event.type == EventType.AGGRESSION:
            delta = self._AGGRESSION_LOSS * event.aggression_score
            self._apply_delta(delta)
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=-5.0,
                trust_delta=delta,
                priority=2,
                reason="aggression",
            )

        if event.type == EventType.REPAIR:
            # La disculpa recupera trust, pero nunca de golpe
            delta = self._REPAIR_GAIN * event.repair_score
            self._apply_delta(delta)
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=+2.0,
                trust_delta=delta,
                priority=1,
                reason="recovery",
            )

        if event.type == EventType.MESSAGE:
            if event.sentiment > 0.3:
                self._apply_delta(self._POSITIVE_MSG_GAIN * event.sentiment)
                return EmotionSignal(
                    module=self.name,
                    value=self._value,
                    energy_delta=0.0,
                    trust_delta=self._POSITIVE_MSG_GAIN * event.sentiment,
                    priority=0,
                )
            if event.sentiment < -0.4:
                self._apply_delta(self._COLD_MSG_LOSS)
                return EmotionSignal(
                    module=self.name,
                    value=self._value,
                    energy_delta=0.0,
                    trust_delta=self._COLD_MSG_LOSS,
                    priority=0,
                )

        return None

    def decay(self, hours: float) -> None:
        factor = self._DECAY_RATE ** hours
        self._set(self._value * factor)

    @property
    def level(self) -> str:
        if self._value >= self._LEVEL_HIGH:
            return "trust_high"
        if self._value >= self._LEVEL_MID:
            return "trust_mid"
        return "trust_low"

    @property
    def allows_depth(self) -> bool:
        """True si hay suficiente confianza para respuestas profundas."""
        return self._value >= self._LEVEL_MID