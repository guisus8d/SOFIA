# core/emotion/modules/curiosity.py
# ============================================================
# Módulo: Curiosity
# Sube con preguntas, temas nuevos, cambios de tema.
# Baja con flood, mensajes repetitivos, respuestas sin contenido.
# Decay lento — la curiosidad es parte de la personalidad base.
# ============================================================

from typing import Optional
from core.emotion.base_emotion import BaseEmotion, EmotionSignal
from core.emotion.event_bus import EmotionEvent, EventType


class Curiosity(BaseEmotion):
    name = "curiosity"
    INITIAL_VALUE = 65.0   # Sofía es naturalmente curiosa

    # ── Constantes deterministas ────────────────────────────
    _QUESTION_GAIN      =  8.0    # usuario hizo una pregunta
    _NEW_TOPIC_GAIN     =  10.0   # topic_shift detectado
    _FLOOD_PENALTY      = -12.0   # mensaje vacío / basura
    _REPEAT_PENALTY     = -6.0    # mensaje repetido
    _RICH_MESSAGE_GAIN  =  5.0    # mensaje largo y con contenido
    _DECAY_RATE         =  0.995  # decay muy lento

    # Largo mínimo para considerar un mensaje "rico"
    _RICH_LEN_THRESHOLD = 40

    def on_event(self, event: EmotionEvent) -> Optional[EmotionSignal]:
        if event.type == EventType.MESSAGE:
            delta = 0.0

            if event.is_question:
                delta += self._QUESTION_GAIN

            if event.message_len >= self._RICH_LEN_THRESHOLD:
                delta += self._RICH_MESSAGE_GAIN

            if event.message_len == 0:
                delta += self._FLOOD_PENALTY

            self._apply_delta(delta)

            if delta != 0:
                return EmotionSignal(
                    module=self.name,
                    value=self._value,
                    energy_delta=delta * 0.15,   # curiosidad da poca energía directa
                    trust_delta=0.0,
                    priority=0,
                )
            return None

        if event.type == EventType.TOPIC_SHIFT:
            self._apply_delta(self._NEW_TOPIC_GAIN)
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=+2.0,
                trust_delta=0.0,
                priority=0,
            )

        if event.type == EventType.IGNORE:
            # Flood / mensajes sin sentido matan la curiosidad
            self._apply_delta(self._FLOOD_PENALTY)
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=-3.0,
                trust_delta=0.0,
                priority=0,
            )

        return None

    def decay(self, hours: float) -> None:
        # Curiosidad es rasgo de personalidad — casi no decae
        factor = self._DECAY_RATE ** hours
        # Pero tiene un mínimo: nunca baja de 30 (rasgo permanente)
        new_val = max(30.0, self._value * factor)
        self._set(new_val)

    @property
    def drives_initiative(self) -> bool:
        """True si la curiosidad es suficiente para tomar iniciativa."""
        return self._value >= 70.0