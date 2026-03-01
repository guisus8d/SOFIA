# core/emotion/event_bus.py
# ============================================================
# SocialBot — Event Bus
# Eventos tipados que disparan los módulos emocionales.
# El decision_engine emite eventos; los módulos los consumen.
# Nunca hay llamada directa módulo ↔ engine.
# ============================================================

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EventType(Enum):
    MESSAGE        = "message"       # usuario envió un mensaje
    AFFECTION      = "affection"     # usuario expresó afecto
    AGGRESSION     = "aggression"    # usuario fue agresivo
    REPAIR         = "repair"        # usuario se disculpó
    IGNORE         = "ignore"        # usuario ignoró / flood
    TIME_PASSED    = "time_passed"   # decay por tiempo
    MEMORY_RECALL  = "memory_recall" # se recordó algo del usuario
    TOPIC_SHIFT    = "topic_shift"   # cambio de tema brusco


@dataclass
class EmotionEvent:
    """Evento base. Todos los eventos heredan de aquí."""
    type: EventType
    user_id: str
    timestamp: float  # unix timestamp

    # ── campos opcionales por tipo ──────────────────────────
    sentiment: float = 0.0          # -1.0 a 1.0
    aggression_score: float = 0.0   # 0.0 a 1.0
    repair_score: float = 0.0       # 0.0 a 1.0  (calidad del perdón)
    affection_score: float = 0.0    # 0.0 a 1.0
    hours_passed: float = 0.0       # para TIME_PASSED
    message_len: int = 0            # largo del mensaje original
    is_question: bool = False       # ¿viene con pregunta?
    is_flood: bool = False          # mensaje basura / spam de caracteres
    keywords: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)


# ── Constructores de conveniencia ─────────────────────────

def message_event(
    user_id: str,
    timestamp: float,
    sentiment: float,
    message_len: int = 0,
    is_question: bool = False,
    is_flood: bool = False,
    keywords: list = None,
) -> EmotionEvent:
    return EmotionEvent(
        type=EventType.MESSAGE,
        user_id=user_id,
        timestamp=timestamp,
        sentiment=sentiment,
        message_len=message_len,
        is_question=is_question,
        is_flood=is_flood,
        keywords=keywords or [],
    )


def aggression_event(
    user_id: str,
    timestamp: float,
    aggression_score: float,
    sentiment: float = -1.0,
) -> EmotionEvent:
    return EmotionEvent(
        type=EventType.AGGRESSION,
        user_id=user_id,
        timestamp=timestamp,
        aggression_score=aggression_score,
        sentiment=sentiment,
    )


def repair_event(
    user_id: str,
    timestamp: float,
    repair_score: float,
    sentiment: float = 0.3,
) -> EmotionEvent:
    return EmotionEvent(
        type=EventType.REPAIR,
        user_id=user_id,
        timestamp=timestamp,
        repair_score=repair_score,
        sentiment=sentiment,
    )


def affection_event(
    user_id: str,
    timestamp: float,
    affection_score: float,
    sentiment: float = 0.8,
) -> EmotionEvent:
    return EmotionEvent(
        type=EventType.AFFECTION,
        user_id=user_id,
        timestamp=timestamp,
        affection_score=affection_score,
        sentiment=sentiment,
    )


def time_event(
    user_id: str,
    timestamp: float,
    hours_passed: float,
) -> EmotionEvent:
    return EmotionEvent(
        type=EventType.TIME_PASSED,
        user_id=user_id,
        timestamp=timestamp,
        hours_passed=hours_passed,
    )