# core/emotion/base_emotion.py
# ============================================================
# SocialBot — Base Emotion (interfaz)
# Todo módulo emocional implementa esta interfaz.
#
# Contrato:
#   - on_event(event) → EmotionSignal | None
#     Lógica 100% determinista. Sin random aquí.
#   - decay(hours) → None
#     El módulo reduce su valor interno con el tiempo.
#   - value → float (0.0 – 100.0)
#     Estado actual del módulo.
#
# La variación aleatoria SOLO ocurre en la capa de expresión
# (sofia_voice.py), nunca dentro de un módulo.
# ============================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EmotionSignal:
    """
    Señal que un módulo emite tras procesar un evento.

    energy_delta y trust_delta son los cambios que este módulo
    propone. El registry los combina y resuelve conflictos.
    priority controla quién gana cuando dos módulos se oponen.
    """
    module: str                   # nombre del módulo emisor
    value: float                  # valor interno resultante (0–100)
    energy_delta: float = 0.0     # cambio propuesto en energía
    trust_delta: float  = 0.0     # cambio propuesto en confianza
    priority: int       = 0       # 0=normal, 1=importante, 2=crítico
    reason: str         = ""      # etiqueta para mood_reason
    meta: dict          = field(default_factory=dict)

    def __post_init__(self):
        self.value = max(0.0, min(100.0, self.value))


class BaseEmotion(ABC):
    """
    Interfaz que todo módulo emocional debe implementar.

    Cada módulo tiene su propio estado interno (self._value)
    que evoluciona con eventos y decae con el tiempo.
    """

    #: Nombre único del módulo (override en subclase)
    name: str = "base"

    #: Valor inicial del módulo
    INITIAL_VALUE: float = 50.0

    def __init__(self):
        self._value: float = self.INITIAL_VALUE

    # ── API pública ──────────────────────────────────────────

    @property
    def value(self) -> float:
        return self._value

    @abstractmethod
    def on_event(self, event) -> Optional[EmotionSignal]:
        """
        Procesa un evento y retorna una señal (o None si no aplica).
        DEBE ser determinista — no usar random aquí.
        """

    @abstractmethod
    def decay(self, hours: float) -> None:
        """
        Reduce el valor interno según el tiempo transcurrido.
        Cada módulo define su propia velocidad de decay.
        """

    # ── Helpers internos ─────────────────────────────────────

    def _clamp(self, v: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, v))

    def _set(self, v: float) -> None:
        self._value = self._clamp(v)

    def _apply_delta(self, delta: float) -> None:
        self._set(self._value + delta)

    def to_dict(self) -> dict:
        return {"module": self.name, "value": round(self._value, 2)}

    def __repr__(self) -> str:
        return f"{self.name}({self._value:.1f})"