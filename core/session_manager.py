# core/session_manager.py
# ============================================================
# SocialBot v0.9.1
# CAMBIOS vs v0.8.0:
#   - FIX BUG: Reconciliación ahora tiene prioridad sobre modo noche.
#     Antes, si el usuario regresaba de noche después de irse enojado,
#     recibía saludo genérico nocturno en vez de "la última vez no
#     quedamos muy bien". Ahora la reconciliación siempre aparece primero.
#   - FIX BUG: Las 5am ya no clasifican como "noche". Antes el rango
#     madrugada (0-4) y noche (>=22 o <6) se solapaban en la hora 5,
#     dejándola huérfana de madrugada. Corregido a <6 consistente.
#   - MANTIENE: todo lo demás de v0.8.0
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
    # Saludos de reconciliación
    "reconciliacion": [
        "Hola… la última vez no quedamos muy bien. ¿Estás mejor?",
        "Oye… la otra vez me quedé pensando. ¿Todo ok?",
        "Holi. Espero que hoy sea mejor que la última vez. ¿Cómo estás?",
    ],
    # Saludos nocturnos
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
          1. Reconciliación si última sesión fue negativa  ← FIX: ahora es PRIMERA prioridad
          2. Modo noche / madrugada (hora actual)
          3. Días hablando (si son ≥ 3 sesiones)
          4. Tema relevante de la última sesión
          5. Usuario conocido sin temas
          6. Usuario nuevo
        """
        session = self.db.load_last_session(user_id)

        if not session:
            # Usuario nuevo — verificar hora antes de dar bienvenida genérica
            night_greeting = self._night_greeting()
            if night_greeting:
                return night_greeting
            return pick(SALUDOS["nuevo"])

        last_tone = session.get("last_session_tone", "neutral")

        # 1. Reconciliación — prioridad máxima, no importa la hora
        if last_tone == "negative":
            return pick(SALUDOS["reconciliacion"])

        # 2. Modo noche / madrugada
        night_greeting = self._night_greeting()
        if night_greeting:
            return night_greeting

        days          = self._days_since(session["date"])
        session_count = session.get("session_count", 1)
        topics        = session.get("topics", [])
        facts         = session.get("important_facts", {})

        # 3. Días hablando (FIX histórico: usamos `days`, no `session_count`)
        if session_count >= 3:
            frase = pick(SALUDOS["dias_hablando"])
            return frase.format(days=days)

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
        """
        Retorna saludo nocturno según la hora actual.
        FIX v0.9.1: madrugada cubre 0-5, noche cubre 22-23 y se solapa
        con el inicio correcto del día (hour < 6 para ambos rangos nocturnos).
        """
        hour = datetime.now().hour
        # Madrugada: 00:00 - 05:59
        if 0 <= hour < 6:
            return pick(SALUDOS["madrugada"])
        # Noche: 22:00 - 23:59
        if hour >= settings.NIGHT_MODE_START_HOUR:
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