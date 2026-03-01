# core/emotion/modules/affection.py
# ============================================================
# Módulo: Affection
# Sube con afecto, halagos, mensajes cálidos.
# Baja con agresión y mensajes fríos sostenidos.
# Decay lento — el cariño no se olvida de golpe.
# ============================================================

from typing import Optional
from core.emotion.base_emotion import BaseEmotion, EmotionSignal
from core.emotion.event_bus import EmotionEvent, EventType


class Affection(BaseEmotion):
    name = "affection"
    INITIAL_VALUE = 50.0

    # ── Constantes deterministas ────────────────────────────
    _AFFECTION_GAIN     =  12.0   # afecto explícito
    _SENTIMENT_SCALE    =   8.0   # impacto por sentimiento positivo
    _AGGRESSION_PENALTY = -15.0   # agresión reduce el afecto
    _REPAIR_GAIN        =   6.0   # disculpa recupera algo
    _DECAY_RATE         =  0.98   # decay por hora (muy lento)

    def on_event(self, event: EmotionEvent) -> Optional[EmotionSignal]:
        if event.type == EventType.AFFECTION:
            delta = self._AFFECTION_GAIN * event.affection_score
            self._apply_delta(delta)
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=+8.0,
                trust_delta=+5.0,
                priority=1,
                reason="affection",
            )

        if event.type == EventType.AGGRESSION:
            delta = self._AGGRESSION_PENALTY * event.aggression_score
            self._apply_delta(delta)
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=-6.0,
                trust_delta=-8.0,
                priority=2,
                reason="aggression",
            )

        if event.type == EventType.REPAIR:
            delta = self._REPAIR_GAIN * event.repair_score
            self._apply_delta(delta)
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=+4.0,
                trust_delta=+6.0,
                priority=1,
                reason="recovery",
            )

        if event.type == EventType.MESSAGE:
            if event.sentiment > 0.4:
                delta = self._SENTIMENT_SCALE * event.sentiment
                self._apply_delta(delta)
                return EmotionSignal(
                    module=self.name,
                    value=self._value,
                    energy_delta=+3.0,
                    trust_delta=+2.0,
                    priority=0,
                    reason="good_vibes",
                )
            if event.sentiment < -0.3:
                delta = self._SENTIMENT_SCALE * event.sentiment  # negativo
                self._apply_delta(delta)
                return EmotionSignal(
                    module=self.name,
                    value=self._value,
                    energy_delta=-2.0,
                    trust_delta=-1.0,
                    priority=0,
                )

        return None

    def decay(self, hours: float) -> None:
        # El afecto decae muy lento — relación construida
        factor = self._DECAY_RATE ** hours
        self._set(self._value * factor)