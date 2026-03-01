# core/emotion/emotion_registry.py
# ============================================================
# SocialBot — Emotion Registry v0.12.3
# CAMBIOS vs v0.12.2:
#   - FIX Bug VERBOSITY #6: flood explícito forzaba verbosity="verbose"
#     cuando fatigue aún no alcanzaba _THRESHOLD_MED (conversación corta).
#     Ahora el registry registra si el evento fue flood (_last_event_was_flood)
#     y en _derive_expression_hints fuerza mínimo "medium" si verbosity
#     seguía en "verbose". Flood = intención de ruido → respuesta corta siempre.
#   - MANTIENE: todo lo demás de v0.12.2 intacto.
# ============================================================
# Orquesta todos los módulos emocionales.
#
# Flujo:
#   1. Recibe un EmotionEvent
#   2. Lo pasa a todos los módulos registrados
#   3. Recolecta EmotionSignal de cada uno
#   4. Resuelve conflictos por prioridad
#   5. Aplica deltas al EmotionalState
#   6. Deriva tono, iniciativa y verbosidad
#   7. Retorna EmotionalState actualizado
#
# Determinista: mismo input → mismo output.
# Sin random. La variación de expresión es responsabilidad
# de sofia_voice.py, no del registry.
# ============================================================

from typing import Optional
from models.state import EmotionalState, Emotion
from core.emotion.base_emotion import EmotionSignal
from core.emotion.event_bus import EmotionEvent, EventType
from core.emotion.modules.affection import Affection
from core.emotion.modules.anger import Anger
from core.emotion.modules.curiosity import Curiosity
from core.emotion.modules.fatigue import Fatigue
from core.emotion.modules.trust import Trust


# ── Constantes de derivación ─────────────────────────────

_MAX_DELTA_PER_EVENT = 4.0    # cap por evento (evita saltos extremos)


class EmotionRegistry:
    """
    Singleton por usuario. Cada usuario tiene su propio registry.
    El session_manager es responsable de crear / cargar instancias.
    """

    def __init__(self):
        # ── Módulos activos ──────────────────────────────
        self.affection = Affection()
        self.anger     = Anger()
        self.curiosity = Curiosity()
        self.fatigue   = Fatigue()
        self.trust     = Trust()

        self._modules = [
            self.affection,
            self.anger,
            self.curiosity,
            self.fatigue,
            self.trust,
        ]

        # Razón del estado actual (para mood_reason)
        self._last_reason: str = ""
        # Flag: el último evento procesado fue flood (para override de verbosity)
        self._last_event_was_flood: bool = False

    # ==========================================================
    # API PRINCIPAL
    # ==========================================================

    def process(
        self,
        event: EmotionEvent,
        state: EmotionalState,
    ) -> EmotionalState:
        """
        Procesa un evento y retorna el EmotionalState actualizado.
        Modifica `state` in-place y también lo retorna.
        """
        # 1. Aplicar decay por tiempo si corresponde
        if event.type == EventType.TIME_PASSED:
            self._apply_decay(event.hours_passed, state)
            return state

        # 2. Recolectar señales de todos los módulos
        signals: list[EmotionSignal] = []
        for module in self._modules:
            sig = module.on_event(event)
            if sig is not None:
                signals.append(sig)

        # 3. Resolver conflictos y acumular deltas
        energy_delta, trust_delta = self._resolve(signals)

        # 4. Aplicar deltas con cap
        state.energy = self._clamp(state.energy + energy_delta)
        state.trust  = self._clamp(state.trust  + trust_delta)

        # 5. Derivar emoción primaria
        self._derive_primary_emotion(state)

        # 6. Registrar si el evento fue flood (para override de verbosity)
        self._last_event_was_flood = getattr(event, "is_flood", False)

        # 7. Derivar tone / initiative / verbosity
        self._derive_expression_hints(state)

        # 7. Guardar razón para mood_reason
        self._last_reason = self._pick_reason(signals)

        state.last_updated = event.timestamp
        return state

    def apply_decay(self, hours: float, state: EmotionalState) -> EmotionalState:
        """Aplica decay temporal directamente (para restaurar desde DB)."""
        self._apply_decay(hours, state)
        return state

    # ==========================================================
    # RESOLUCIÓN DE CONFLICTOS
    # ==========================================================

    def _resolve(
        self,
        signals: list[EmotionSignal],
    ) -> tuple[float, float]:
        """
        Combina señales en un delta neto de energía y trust.

        Regla de prioridad:
        - Si hay señales de prioridad 2 (crítico), solo se usan esas.
        - Si hay señales de prioridad 1 (importante), se promedian
          entre sí y se suman las de prioridad 0.
        - Prioridad 0: todas se suman normalmente.

        Cap final: ±_MAX_DELTA_PER_EVENT
        """
        if not signals:
            return 0.0, 0.0

        max_priority = max(s.priority for s in signals)

        if max_priority == 2:
            # Solo señales críticas
            dominant = [s for s in signals if s.priority == 2]
        elif max_priority == 1:
            # Señales importantes + las de prioridad 0 con peso reducido
            dominant = [s for s in signals if s.priority >= 1]
            support  = [s for s in signals if s.priority == 0]
            # Soporte contribuye 30%
            support_e = sum(s.energy_delta for s in support) * 0.30
            support_t = sum(s.trust_delta  for s in support) * 0.30
        else:
            dominant = signals
            support_e = support_t = 0.0

        energy = sum(s.energy_delta for s in dominant)
        trust  = sum(s.trust_delta  for s in dominant)

        if max_priority == 1:
            energy += support_e
            trust  += support_t

        # Cap
        energy = max(-_MAX_DELTA_PER_EVENT, min(_MAX_DELTA_PER_EVENT, energy))
        trust  = max(-_MAX_DELTA_PER_EVENT, min(_MAX_DELTA_PER_EVENT, trust))

        return energy, trust

    # ==========================================================
    # DERIVACIÓN DE EMOCIÓN PRIMARIA
    # ==========================================================

    def _derive_primary_emotion(self, state: EmotionalState) -> None:
        """
        Determinista: mismos valores → misma emoción.
        Usa anger.is_high para detectar enojo aunque energy sea media.
        """
        e = state.energy
        t = state.trust

        if self.anger.is_high:
            state.primary_emotion = Emotion.ANGRY
        elif e > 65 and t > 60:
            state.primary_emotion = Emotion.HAPPY
        elif e < 25:
            state.primary_emotion = Emotion.SAD
        elif t < 25:
            state.primary_emotion = Emotion.ANGRY
        elif e < 40 and t < 40:
            state.primary_emotion = Emotion.FEARFUL
        else:
            state.primary_emotion = Emotion.NEUTRAL

    # ==========================================================
    # DERIVACIÓN DE EXPRESSION HINTS
    # Estos valores van al EmotionalState y son consumidos por
    # sofia_voice.py para elegir entre variantes de respuesta.
    # NO hay random aquí.
    # ==========================================================

    def _derive_expression_hints(self, state: EmotionalState) -> None:
        """
        Deriva tone, initiative y verbosity a partir del estado
        de los módulos. 100% determinista.
        """
        e = state.energy
        t = state.trust

        # ── TONE ────────────────────────────────────────────
        # FIX v0.12.1: warm/playful usan valores de módulos directamente.
        # FIX v0.12.2: post-recovery, anger.is_active puede seguir True aunque
        # anger.value haya bajado al rango medio-bajo. Se añade comprobación
        # de trust para no quedar atascado en slightly_cold indefinidamente.
        if self.anger.is_high or t < 20:
            tone = "cold"
        elif (self.anger.is_active or t < 35) and self.trust.value < 45:
            # is_active solo bloquea el tone si trust todavía es bajo.
            # Si trust ya subió (recovery avanzó), dejar subir el tone.
            tone = "slightly_cold"
        elif self.affection.value > 65 and self.trust.value > 65:
            tone = "warm"
        elif self.affection.value > 50 and self.trust.value > 50:
            tone = "playful"
        elif t >= 35 and not self.anger.is_high:
            # Post-recovery con trust recuperándose — al menos neutral
            tone = "neutral"
        else:
            tone = "neutral"

        # ── INITIATIVE ──────────────────────────────────────
        if self.fatigue.suppresses_initiative or e < 30:
            initiative = "low"
        elif self.curiosity.drives_initiative and e > 55:
            initiative = "high"
        else:
            initiative = "medium"

        # ── VERBOSITY ───────────────────────────────────────
        verbosity = self.fatigue.verbosity_hint
        # Trust bajo también acorta respuestas
        if t < 30 and verbosity != "brief":
            verbosity = "medium"
        # FIX v0.12.3: flood explícito → mínimo "medium" aunque fatigue sea baja.
        # Flood indica ruido sin intención semántica — respuesta corta siempre.
        # No aplica si ya era "brief" (fatigue alta lo resuelve sola).
        if getattr(self, "_last_event_was_flood", False) and verbosity == "verbose":
            verbosity = "medium"

        # Guardar en state (campos extendidos)
        state.tone       = tone
        state.initiative = initiative
        state.verbosity  = verbosity

    # ==========================================================
    # DECAY
    # ==========================================================

    def _apply_decay(self, hours: float, state: EmotionalState) -> None:
        if hours <= 0:
            return

        for module in self._modules:
            module.decay(hours)

        # Re-derivar después del decay
        self._derive_primary_emotion(state)
        self._derive_expression_hints(state)

    # ==========================================================
    # UTILIDADES
    # ==========================================================

    def _pick_reason(self, signals: list[EmotionSignal]) -> str:
        # La razón de mayor prioridad gana
        with_reason = [s for s in signals if s.reason]
        if not with_reason:
            return ""
        return max(with_reason, key=lambda s: s.priority).reason

    @property
    def last_reason(self) -> str:
        return self._last_reason

    def _clamp(self, v: float) -> float:
        return max(0.0, min(100.0, v))

    def snapshot(self) -> dict:
        """Estado actual de todos los módulos (para debug/logs)."""
        return {m.name: round(m.value, 1) for m in self._modules}

    def to_dict(self) -> dict:
        return {
            "modules": self.snapshot(),
            "last_reason": self._last_reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EmotionRegistry":
        """Restaura el registry desde datos serializados."""
        registry = cls()
        modules_data = data.get("modules", {})
        module_map = {m.name: m for m in registry._modules}
        for name, value in modules_data.items():
            if name in module_map:
                module_map[name]._set(value)
        registry._last_reason = data.get("last_reason", "")
        return registry