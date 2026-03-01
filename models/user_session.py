# models/user_session.py
# ============================================================
# UserSession — estado conversacional por usuario.
# Extraído de DecisionEngine en v0.13.1
#
# Antes: 11 diccionarios dispersos dentro del engine.
# Ahora: un objeto por usuario, serializable, swappable a Redis.
#
# IMPORTANTE: este es estado IN-MEMORY de la conversación activa.
# No confundir con SessionManager (persistencia entre sesiones/días).
# ============================================================

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional


@dataclass
class UserSession:
    """
    Todo el estado mutable por usuario que necesita el DecisionEngine.

    Campos:
        msg_counter          — número de mensaje en la conversación actual
        aggression_count     — cuántas agresiones acumuladas sin resolver
        recovery_needed      — cuántos mensajes de recovery faltan
        short_streak         — racha de mensajes cortos consecutivos
        last_message         — último mensaje normalizado (anti-repetición)
        repeat_count         — veces que repitió el mismo mensaje
        last_was_confession  — el turno anterior fue una confesión emocional
        secrets_revealed     — cuántos secretos reveló hoy
        secrets_date         — fecha del último reset de secretos
        output_cooldowns     — cooldowns por tipo de output (semantic, quote, etc.)
        topic_question_history — historial de preguntas por topic lock
    """

    msg_counter:             int                  = 0
    aggression_count:        int                  = 0
    recovery_needed:         int                  = 0
    short_streak:            int                  = 0
    last_message:            str                  = ""
    repeat_count:            int                  = 0
    last_was_confession:     bool                 = False
    secrets_revealed:        int                  = 0
    secrets_date:            Optional[date]       = None
    output_cooldowns:        Dict[str, int]        = field(default_factory=dict)
    topic_question_history:  List[str]            = field(default_factory=list)

    # ── Serialización (para Redis en el futuro) ──────────────

    def to_dict(self) -> dict:
        return {
            "msg_counter":             self.msg_counter,
            "aggression_count":        self.aggression_count,
            "recovery_needed":         self.recovery_needed,
            "short_streak":            self.short_streak,
            "last_message":            self.last_message,
            "repeat_count":            self.repeat_count,
            "last_was_confession":     self.last_was_confession,
            "secrets_revealed":        self.secrets_revealed,
            "secrets_date":            self.secrets_date.isoformat() if self.secrets_date else None,
            "output_cooldowns":        self.output_cooldowns,
            "topic_question_history":  self.topic_question_history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserSession":
        raw_date = data.get("secrets_date")
        return cls(
            msg_counter            = data.get("msg_counter", 0),
            aggression_count       = data.get("aggression_count", 0),
            recovery_needed        = data.get("recovery_needed", 0),
            short_streak           = data.get("short_streak", 0),
            last_message           = data.get("last_message", ""),
            repeat_count           = data.get("repeat_count", 0),
            last_was_confession    = data.get("last_was_confession", False),
            secrets_revealed       = data.get("secrets_revealed", 0),
            secrets_date           = date.fromisoformat(raw_date) if raw_date else None,
            output_cooldowns       = data.get("output_cooldowns", {}),
            topic_question_history = data.get("topic_question_history", []),
        )

    # ── Helpers de conveniencia ──────────────────────────────

    @property
    def has_active_conflict(self) -> bool:
        """True si hay agresión o recovery pendiente."""
        return self.aggression_count > 0 or self.recovery_needed > 0

    def cooldown_ok(self, output_type: str, current_msg_n: int, min_gap: int) -> bool:
        last_used = self.output_cooldowns.get(output_type, -999)
        return (current_msg_n - last_used) >= min_gap

    def mark_cooldown(self, output_type: str, current_msg_n: int) -> None:
        self.output_cooldowns[output_type] = current_msg_n

    def reset_conflict(self) -> None:
        """Limpia el ciclo de agresión/recovery completamente."""
        self.aggression_count = 0
        self.recovery_needed  = 0

    def daily_secrets_reset_if_needed(self) -> None:
        """Resetea el contador de secretos si cambió el día."""
        today = date.today()
        if self.secrets_date != today:
            self.secrets_revealed = 0
            self.secrets_date     = today