# discord/channel_memory.py
# ============================================================
# ChannelMemory — Memoria colectiva del canal de Discord
# v2 — keywords sueltas + sin utcnow deprecations
# ============================================================

from __future__ import annotations

import unicodedata
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ChannelEvent:
    ts:        datetime
    text:      str
    sentiment: Optional[float]
    topics:    list[str]
    is_heavy:  bool


@dataclass
class TopicAccumulation:
    key:        str
    value:      str
    count:      int      = 0
    first_seen: datetime = field(default_factory=_now)
    last_seen:  datetime = field(default_factory=_now)

    @property
    def density(self) -> float:
        elapsed = (self.last_seen - self.first_seen).total_seconds() / 3600
        return self.count / max(elapsed, 0.1)

    @property
    def span_hours(self) -> float:
        return (self.last_seen - self.first_seen).total_seconds() / 3600


@dataclass
class InitiativeReason:
    reason_type: str
    topic_key:   Optional[str]
    topic_value: Optional[str]
    strength:    float
    description: str


# ─── constantes ───────────────────────────────────────────────

_HEAVY_PHRASES = [
    "me quiero morir", "quiero morirme", "no quiero vivir",
    "estoy muy mal", "no puedo mas", "no puedo más",
    "me odio", "me lastimo", "me corto",
    "me quiero ir", "ya no aguanto",
]

_CONFLICT_PHRASES = [
    "callate", "cállate", "eres un idiot", "eres una idiot",
    "odio a", "me cae mal", "te odio", "asco de",
    "eres lo peor", "no sirves",
]

_TALKABLE_TOPICS = {
    "musica_genero", "deporte_interes", "hobby",
    "comida_favorita", "ocupacion",
}

_BURST_THRESHOLD   = 6
_PERSISTENCE_HOURS = 2.0

# topic_id, key, value, keywords
_TOPIC_KEYWORDS: list[tuple[str, str, str, list[str]]] = [
    ("musica_genero:metal",     "musica_genero",   "metal",       ["metal", "metalero", "riff", "thrash", "doom", "heavy metal", "death metal", "black metal"]),
    ("musica_genero:rock",      "musica_genero",   "rock",        ["rock", "rockero", "punk", "grunge", "indie"]),
    ("musica_genero:rap",       "musica_genero",   "rap",         ["rap", "trap", "flow", "freestyle", "hiphop", "hip hop", "mc"]),
    ("musica_genero:reggaeton", "musica_genero",   "reggaeton",   ["reggaeton", "perreo", "urbano", "dembow"]),
    ("musica_genero:pop",       "musica_genero",   "pop",         ["pop", "charts", "spotify"]),
    ("musica_genero:clasica",   "musica_genero",   "clasica",     ["clasica", "clasico", "orchestra", "violin"]),
    ("deporte_interes:futbol",  "deporte_interes", "futbol",      ["futbol", "fútbol", "partido", "gol", "liga", "cancha", "portero", "champions"]),
    ("deporte_interes:gym",     "deporte_interes", "gym",         ["gym", "gimnasio", "entreno", "rutina", "pesas", "cardio", "proteina", "proteína"]),
    ("deporte_interes:basket",  "deporte_interes", "basket",      ["basket", "basquetbol", "nba", "canasta"]),
    ("deporte_interes:tenis",   "deporte_interes", "tenis",       ["tenis", "raqueta", "atp", "wimbledon"]),
    ("hobby:videojuegos",       "hobby",           "videojuegos", ["juego", "gaming", "gamer", "steam", "ps5", "xbox", "nintendo", "lag"]),
    ("hobby:dibujar",           "hobby",           "dibujar",     ["dibujo", "arte", "ilustración", "sketch", "procreate", "fanart"]),
    ("hobby:programar",         "hobby",           "programar",   ["código", "codigo", "bug", "deploy", "commit", "programar", "backend", "frontend"]),
    ("hobby:leer",              "hobby",           "leer",        ["libro", "novela", "lectura", "leer", "autor", "capitulo"]),
    ("hobby:cocinar",           "hobby",           "cocinar",     ["receta", "cocinar", "cocinando", "platillo", "ingredientes"]),
    ("comida_favorita:pizza",   "comida_favorita", "pizza",       ["pizza", "pepperoni"]),
    ("comida_favorita:tacos",   "comida_favorita", "tacos",       ["tacos", "taqueria", "taquero"]),
    ("comida_favorita:ramen",   "comida_favorita", "ramen",       ["ramen", "fideos", "caldo japonés"]),
    ("comida_favorita:sushi",   "comida_favorita", "sushi",       ["sushi", "nigiri", "maki", "wasabi"]),
]


class ChannelMemory:

    def __init__(self, window_hours: float = 24.0, max_events: int = 300):
        self._window         = timedelta(hours=window_hours)
        self._events: deque[ChannelEvent]          = deque(maxlen=max_events)
        self._topics: dict[str, TopicAccumulation] = {}
        self._conflict_ts:   Optional[datetime]    = None
        self._last_heavy_ts: Optional[datetime]    = None

        from core.semantic_memory import SemanticMemory
        self._sem = SemanticMemory()

    def ingest(self, text: str, sentiment: Optional[float] = None, ts: Optional[datetime] = None) -> ChannelEvent:
        ts   = ts or _now()
        norm = self._normalize(text)

        is_heavy    = any(p in norm for p in _HEAVY_PHRASES)
        is_conflict = any(p in norm for p in _CONFLICT_PHRASES)

        # 1. Frases exactas via SemanticMemory
        raw_facts = self._sem.extract_facts(text)
        topic_ids = []
        for key, val in raw_facts.items():
            if key in _TALKABLE_TOPICS:
                tid = f"{key}:{val}"
                self._accumulate(tid, key, val, ts)
                topic_ids.append(tid)

        # 2. Keywords sueltas — conversación natural
        for tid, key, val, keywords in _TOPIC_KEYWORDS:
            if tid in topic_ids:
                continue
            if any(kw in norm for kw in keywords):
                self._accumulate(tid, key, val, ts)
                topic_ids.append(tid)

        event = ChannelEvent(ts=ts, text=text, sentiment=sentiment,
                             topics=topic_ids, is_heavy=is_heavy)
        self._events.append(event)

        if is_heavy:
            self._last_heavy_ts = ts
        if is_conflict:
            self._conflict_ts = ts

        self._prune()
        return event

    def _accumulate(self, topic_id: str, key: str, val: str, ts: datetime):
        if topic_id not in self._topics:
            self._topics[topic_id] = TopicAccumulation(key=key, value=val, first_seen=ts, last_seen=ts)
        acc           = self._topics[topic_id]
        acc.count    += 1
        acc.last_seen = ts

    @property
    def last_heavy_ts(self) -> Optional[datetime]:
        return self._last_heavy_ts

    @property
    def last_conflict_ts(self) -> Optional[datetime]:
        return self._conflict_ts

    def recent_sentiments(self, hours: float = 1.0) -> list[float]:
        cutoff = _now() - timedelta(hours=hours)
        return [e.sentiment for e in self._events if e.ts > cutoff and e.sentiment is not None]

    def conflict_is_recent(self, cooldown_hours: float = 2.0) -> bool:
        if not self._conflict_ts:
            return False
        return _now() - self._conflict_ts < timedelta(hours=cooldown_hours)

    def heavy_is_recent(self, cooldown_hours: float = 4.0) -> bool:
        if not self._last_heavy_ts:
            return False
        return _now() - self._last_heavy_ts < timedelta(hours=cooldown_hours)

    def get_initiative_reason(self) -> Optional[InitiativeReason]:
        now = _now()

        if (
            self._conflict_ts
            and timedelta(minutes=30) < (now - self._conflict_ts) < timedelta(hours=3)
            and not self.heavy_is_recent(1.0)
        ):
            strength = 1.0 - ((now - self._conflict_ts).total_seconds() / 10800)
            return InitiativeReason(
                reason_type="post_conflict", topic_key=None, topic_value=None,
                strength=round(strength, 2),
                description=f"Conflicto hace {int((now - self._conflict_ts).total_seconds() / 60)} min",
            )

        burst = self._find_burst(now)
        if burst:
            return burst

        persistence = self._find_persistence(now)
        if persistence:
            return persistence

        return None

    def _find_burst(self, now: datetime) -> Optional[InitiativeReason]:
        window = timedelta(hours=1)
        for topic_id, acc in self._topics.items():
            if now - acc.last_seen > timedelta(hours=2):
                continue
            recent_count = sum(
                1 for e in self._events
                if e.ts > now - window and topic_id in e.topics
            )
            if recent_count >= _BURST_THRESHOLD:
                strength = min(1.0, recent_count / (_BURST_THRESHOLD * 2))
                return InitiativeReason(
                    reason_type="topic_burst", topic_key=acc.key, topic_value=acc.value,
                    strength=round(strength, 2),
                    description=f"{acc.value} mencionado {recent_count}x en 1h",
                )
        return None

    def _find_persistence(self, now: datetime) -> Optional[InitiativeReason]:
        best: Optional[tuple[float, TopicAccumulation]] = None
        for acc in self._topics.values():
            if now - acc.last_seen > timedelta(hours=1):
                continue
            if acc.span_hours >= _PERSISTENCE_HOURS and acc.count >= 3:
                score = acc.span_hours * acc.density
                if best is None or score > best[0]:
                    best = (score, acc)
        if best:
            _, acc = best
            strength = min(1.0, acc.span_hours / 6.0)
            return InitiativeReason(
                reason_type="topic_persistence", topic_key=acc.key, topic_value=acc.value,
                strength=round(strength, 2),
                description=f"{acc.value} activo {acc.span_hours:.1f}h ({acc.count} msgs)",
            )
        return None

    def _normalize(self, text: str) -> str:
        nfkd = unicodedata.normalize("NFD", text)
        return nfkd.encode("ascii", "ignore").decode("utf-8").lower().strip()

    def _prune(self):
        cutoff = _now() - self._window
        dead   = [k for k, acc in self._topics.items() if acc.last_seen < cutoff]
        for k in dead:
            del self._topics[k]

    def debug_summary(self) -> dict:
        return {
            "total_events":      len(self._events),
            "active_topics":     {
                k: {"count": v.count, "span_h": round(v.span_hours, 1), "density": round(v.density, 2)}
                for k, v in self._topics.items()
            },
            "last_heavy":        str(self._last_heavy_ts) if self._last_heavy_ts else None,
            "last_conflict":     str(self._conflict_ts) if self._conflict_ts else None,
            "initiative_reason": str(self.get_initiative_reason()),
        }