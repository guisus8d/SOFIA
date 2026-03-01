# core/emotion/modules/fatigue.py
# ============================================================
# Módulo: Fatigue
# Sube con conversaciones largas, flood, repetición.
# Baja con el tiempo (descanso), mensajes positivos, silencio.
# Afecta verbosidad e iniciativa directamente.
# ============================================================

from typing import Optional
from core.emotion.base_emotion import BaseEmotion, EmotionSignal
from core.emotion.event_bus import EmotionEvent, EventType


class Fatigue(BaseEmotion):
    name = "fatigue"
    INITIAL_VALUE = 10.0   # arranca descansada

    # ── Constantes deterministas ────────────────────────────
    _MESSAGE_COST       =  1.5    # cada mensaje cuesta un poco
    _FLOOD_COST         =  8.0    # flood cansa mucho
    _REPEAT_COST        =  4.0    # repetición es agotadora
    _AGGRESSION_COST    =  6.0    # agresión cansa
    _REST_RECOVERY      = -15.0   # tiempo sin hablar recupera
    _AFFECTION_RECOVERY = -5.0    # afecto reduce fatiga
    _REST_HOURS         =  2.0    # horas de silencio para notar recuperación

    _THRESHOLD_HIGH     =  70.0   # fatiga alta → respuestas cortas
    _THRESHOLD_MED      =  40.0   # fatiga media → menos iniciativa

    def on_event(self, event: EmotionEvent) -> Optional[EmotionSignal]:
        if event.type == EventType.MESSAGE:
            cost = self._MESSAGE_COST
            # FIX v0.12.3: mensaje vacío O spam de caracteres (flood) → FLOOD_COST.
            # "aaaaaaaaaaaa" tiene message_len > 0 pero es basura — detectar via
            # unique_chars ratio si el evento lo incluye, o via message_len muy corto
            # con contenido sin valor semántico.
            _is_char_flood = getattr(event, "is_flood", False)
            if event.message_len == 0 or _is_char_flood:
                cost = self._FLOOD_COST
            self._apply_delta(cost)
            # Fatiga alta → reduce energía
            energy_impact = -1.5 if self._value >= self._THRESHOLD_HIGH else 0.0
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=energy_impact,
                trust_delta=0.0,
                priority=0,
                meta={"verbosity_hint": self._verbosity_hint()},
            )

        if event.type == EventType.IGNORE:
            self._apply_delta(self._FLOOD_COST)
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=-2.0,
                trust_delta=0.0,
                priority=0,
            )

        if event.type == EventType.AFFECTION:
            self._apply_delta(self._AFFECTION_RECOVERY)
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=+2.0,
                trust_delta=0.0,
                priority=0,
            )

        if event.type == EventType.TIME_PASSED:
            # Descanso recupera fatiga
            if event.hours_passed >= self._REST_HOURS:
                recovery = self._REST_RECOVERY * min(event.hours_passed / 4.0, 1.5)
                self._apply_delta(recovery)
            return None  # time decay no emite señal activa

        if event.type == EventType.AGGRESSION:
            self._apply_delta(self._AGGRESSION_COST)
            return EmotionSignal(
                module=self.name,
                value=self._value,
                energy_delta=-3.0,
                trust_delta=0.0,
                priority=1,
            )

        return None

    def decay(self, hours: float) -> None:
        # Fatiga baja naturalmente con el tiempo
        recovery = self._REST_RECOVERY * min(hours / 4.0, 2.0)
        self._apply_delta(recovery)

    @staticmethod
    def is_char_flood(text: str) -> bool:
        """
        FIX v0.12.3: detecta mensajes que son basura/spam de caracteres.
        Casos:
          - Todo el mensaje es el mismo carácter repetido ("aaaaaaaa", ".......")
          - Ratio de caracteres únicos sobre total es muy bajo (< 15%)
            y el mensaje tiene más de 4 caracteres
        Uso: emotion_engine llama esto al construir EmotionEvent para
        setear is_flood=True antes de emitir EventType.MESSAGE.
        """
        if not text or len(text.strip()) == 0:
            return True  # vacío es flood también
        clean = text.strip()
        if len(clean) <= 2:
            return False  # mensajes muy cortos (., ok) son cortos, no flood
        unique = len(set(clean.lower()))
        # 1 carácter único o ratio < 15% con más de 4 chars
        if unique == 1:
            return True
        if len(clean) >= 5 and (unique / len(clean)) < 0.15:
            return True
        return False

    def _verbosity_hint(self) -> str:
        if self._value >= self._THRESHOLD_HIGH:
            return "brief"
        if self._value >= self._THRESHOLD_MED:
            return "medium"
        return "verbose"

    @property
    def verbosity_hint(self) -> str:
        return self._verbosity_hint()

    @property
    def suppresses_initiative(self) -> bool:
        return self._value >= self._THRESHOLD_MED