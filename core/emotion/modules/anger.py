# core/emotion/modules/anger.py
# ============================================================
# Módulo: Anger
# Sube rápido con agresión. Baja lento.
# Con repair_score alto puede bajar más rápido.
# Decay moderado — el enojo no dura para siempre.
# ============================================================

from typing import Optional
from core.emotion.base_emotion import BaseEmotion, EmotionSignal
from core.emotion.event_bus import EmotionEvent, EventType


class Anger(BaseEmotion):
    name = "anger"
    INITIAL_VALUE = 0.0   # arranca sin enojo

    # ── Constantes deterministas ────────────────────────────
    _AGGRESSION_GAIN    =  25.0   # agresión sube el enojo fuerte
    _REPAIR_REDUCTION   = -12.0   # disculpa lo baja
    _DECAY_RATE         =  0.92   # decay por hora (moderado)
    _THRESHOLD_HIGH     =  60.0   # enojo alto → afecta decisiones
    _THRESHOLD_ACTIVE   =  25.0   # enojo activo → tono frío

    def on_event(self, event: EmotionEvent) -> Optional[EmotionSignal]:
        if event.type == EventType.AGGRESSION:
            delta = self._AGGRESSION_GAIN * event.aggression_score
            self._apply_delta(delta)

            # Enojo alto → penaliza energía y trust fuertemente
            priority = 2 if self._value >= self._THRESHOLD_HIGH else 1
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=-10.0 * event.aggression_score,
                trust_delta=-12.0 * event.aggression_score,
                priority=priority,
                reason="aggression",
                meta={"anger_high": self._value >= self._THRESHOLD_HIGH},
            )

        if event.type == EventType.REPAIR:
            # Disculpa reduce enojo, pero depende de qué tan alto estaba
            reduction = self._REPAIR_REDUCTION * event.repair_score
            if self._value >= self._THRESHOLD_HIGH:
                reduction *= 0.6   # enojo alto → más difícil de bajar
            self._apply_delta(reduction)
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=+3.0 * event.repair_score,
                trust_delta=+4.0 * event.repair_score,
                priority=1,
                reason="recovery",
            )

        if event.type == EventType.AFFECTION:
            # Afecto genuino baja el enojo gradualmente
            self._apply_delta(-6.0 * event.affection_score)
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=+2.0,
                trust_delta=+3.0,
                priority=0,
            )

        return None

    def decay(self, hours: float) -> None:
        # El enojo decae solo con el tiempo
        factor = self._DECAY_RATE ** hours
        self._set(self._value * factor)

    @property
    def is_active(self) -> bool:
        return self._value >= self._THRESHOLD_ACTIVE

    @property
    def is_high(self) -> bool:
        return self._value >= self._THRESHOLD_HIGH