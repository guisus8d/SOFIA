# core/session_manager.py
# ============================================================
# SocialBot v0.8.0
# FIX: get_greeting usaba session_count donde debía usar days.
#      "Ya llevamos 47 días" cuando eran 47 sesiones → corregido.
# NUEVO: last_session_tone — Sofía recuerda cómo terminó la conversación.
#        Si el usuario se fue enojado: "La última vez no quedamos muy bien..."
# NUEVO: Saludos según hora del día (modo noche).
# ============================================================

from datetime import datetime
from typing import Optional
from storage.database import Database
from config.sofia_voice import pick
from config import settings
import random


# ============================================================
# SALUDOS CON MEMORIA
# ============================================================

SALUDOS = {
    "nuevo": [
        "¡Holi! Soy Sofía. ¿Cómo estás? 😊",
        "Hola, qué bueno que estás aquí. ¿Cómo te llamas?",
        "¡Oye, hola! Es la primera vez que hablamos, ¿verdad? Cuéntame de ti.",
    ],
    "conocido_sin_temas": [
        "¡Hola! ¿Cómo estás hoy?",
        "Oye, hola. ¿Qué tal tu día?",
        "Holi, ¿cómo vas?",
        "¡Oye! ¿Todo bien por ahí?",
    ],
    "conocido_con_tema": [
        "¡Hola! Oye, la otra vez mencionaste {topic}. ¿Cómo va eso?",
        "Holi 😊 Oye, ¿qué pasó con {topic}?",
        "¡Oye! ¿Cómo te fue con {topic}?",
        "Hola, ¿sigues con lo de {topic}?",
    ],
    # FIX: ahora {days} es el número de DÍAS (variable days), no session_count
    "dias_hablando": [
        "¡Oye! Ya llevamos {days} días hablando, jeje.",
        "Hola 😊 ¿Sabías que ya llevamos {days} días? Qué padre.",
        "Holi. {days} días ya, ¿cómo estás hoy?",
    ],
    # NUEVO v0.8.0 — Saludos de reconciliación
    "reconciliacion": [
        "Hola… la última vez no quedamos muy bien. ¿Estás mejor?",
        "Oye… la otra vez me quedé pensando. ¿Todo ok?",
        "Holi. Espero que hoy sea mejor que la última vez. ¿Cómo estás?",
    ],
    # NUEVO v0.8.0 — Saludos nocturnos
    "noche": [
        "Oye… es tarde. ¿Estás bien?",
        "Mm… ¿sin poder dormir?",
        "Holi. Las horas raras tienen sus propias conversaciones, ¿verdad?",
        "Es tarde. ¿Qué tienes en la cabeza a esta hora?",
    ],
    "madrugada": [
        "Oye… ¿todo bien? Es muy tarde.",
        "Mm… a esta hora la cabeza no para, ¿verdad?",
        "Hola. Pocas personas despiertas a esta hora. ¿Qué pasa?",
    ],
}


class SessionManager:
    def __init__(self, db: Database):
        self.db = db

    # --------------------------------------------------------
    # SALUDO PRINCIPAL
    # --------------------------------------------------------

    def get_greeting(self, user_id: str) -> str:
        """
        Prioridad:
          1. Modo noche / madrugada (hora actual)
          2. Reconciliación si última sesión fue negativa
          3. Días hablando (si son ≥ 3 sesiones)
          4. Tema relevante de la última sesión
          5. Usuario conocido sin temas
          6. Usuario nuevo
        """
        # 1. Modo noche
        night_greeting = self._night_greeting()
        if night_greeting:
            return night_greeting

        session = self.db.load_last_session(user_id)

        if not session:
            return pick(SALUDOS["nuevo"])

        days          = self._days_since(session["date"])
        session_count = session.get("session_count", 1)
        topics        = session.get("topics", [])
        facts         = session.get("important_facts", {})
        last_tone     = session.get("last_session_tone", "neutral")

        # 2. Reconciliación
        if last_tone == "negative":
            return pick(SALUDOS["reconciliacion"])

        # 3. Días hablando (FIX: usamos `days`, no `session_count`)
        if session_count >= 3:
            frase = pick(SALUDOS["dias_hablando"])
            return frase.format(days=days)   # ← FIX: era session_count

        # 4. Tema relevante
        top_topic = self._pick_top_topic(topics, facts)
        if top_topic:
            frase = pick(SALUDOS["conocido_con_tema"])
            return frase.format(topic=top_topic)

        # 5. Conocido sin temas
        return pick(SALUDOS["conocido_sin_temas"])

    # --------------------------------------------------------
    # GUARDAR SESIÓN (incluye tono de cierre)
    # --------------------------------------------------------

    def save_session(self, user_id: str, profile, last_tone: str = "neutral") -> None:
        """
        Guarda resumen de la sesión.
        last_tone: "positive" | "neutral" | "negative"
        """
        last = self.db.load_last_session(user_id)
        session_count = (last["session_count"] + 1) if last else 1

        self.db.save_session(
            user_id=user_id,
            topics=profile.topics,
            important_facts=profile.important_facts,
            session_count=session_count,
            last_session_tone=last_tone,
        )

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------

    def _night_greeting(self) -> Optional[str]:
        """Retorna saludo nocturno según la hora actual."""
        hour = datetime.now().hour
        if 0 <= hour < 5:
            return pick(SALUDOS["madrugada"])
        if hour >= settings.NIGHT_MODE_START_HOUR or hour < settings.NIGHT_MODE_END_HOUR:
            return pick(SALUDOS["noche"])
        return None

    def _days_since(self, date: datetime) -> int:
        delta = datetime.now() - date
        return max(0, delta.days)

    def _pick_top_topic(self, topics: list, facts: dict) -> Optional[str]:
        stopwords = {
            "hola", "bien", "mal", "nada", "algo", "todo",
            "eso", "esto", "aqui", "ahi", "igual", "bueno"
        }

        if facts:
            sorted_facts = sorted(facts.items(), key=lambda x: x[1], reverse=True)
            for fact, weight in sorted_facts:
                if weight >= 2.0:
                    clean = self._clean_fact(fact)
                    if clean:
                        return clean

        for topic in topics:
            if topic.lower() not in stopwords and len(topic) > 3:
                return topic

        return None

    def _clean_fact(self, fact: str) -> str:
        skip_patterns = ["soy ", "tiene ", "es "]
        fact_lower = fact.lower()

        for pattern in skip_patterns:
            if fact_lower.startswith(pattern):
                return ""

        if "gusta" in fact_lower:
            parts = fact_lower.split("gusta")
            if len(parts) > 1:
                topic = parts[1].strip()
                return topic if len(topic) > 2 else ""

        if "estudia" in fact_lower:
            parts = fact_lower.split("estudia")
            if len(parts) > 1:
                return parts[1].strip()

        if "trabaja" in fact_lower:
            parts = fact_lower.split("en")
            if len(parts) > 1:
                return parts[-1].strip()

        return fact