# core/session_manager.py
# ============================================================
# SocialBot v0.5.0 — Session Manager
#
# Responsabilidades:
#   - Al ARRANCAR: cargar la última sesión y generar saludo
#   - Al CERRAR: guardar resumen de la sesión actual
# ============================================================

from datetime import datetime
from typing import Optional
from storage.database import Database
from config.sofia_voice import pick
import random


# ============================================================
# SALUDOS CON MEMORIA
# Sofía recuerda temas y días hablando
# ============================================================

SALUDOS = {

    # Usuario nuevo — primera vez
    "nuevo": [
        "¡Holi! Soy Sofía. ¿Cómo estás? 😊",
        "Hola, qué bueno que estás aquí. ¿Cómo te llamas?",
        "¡Oye, hola! Es la primera vez que hablamos, ¿verdad? Cuéntame de ti.",
    ],

    # Usuario conocido — sin temas guardados
    "conocido_sin_temas": [
        "¡Hola! ¿Cómo estás hoy?",
        "Oye, hola. ¿Qué tal tu día?",
        "Holi, ¿cómo vas?",
        "¡Oye! ¿Todo bien por ahí?",
    ],

    # Usuario conocido — con temas guardados
    # {topic} se reemplaza con el tema más relevante
    "conocido_con_tema": [
        "¡Hola! Oye, la otra vez mencionaste {topic}. ¿Cómo va eso?",
        "Holi 😊 Oye, ¿qué pasó con {topic}?",
        "¡Oye! ¿Cómo te fue con {topic}?",
        "Hola, ¿sigues con lo de {topic}?",
    ],

    # Usuario que lleva varios días
    # {days} se reemplaza con el número de días
    "dias_hablando": [
        "¡Oye! Ya llevamos {days} días hablando, jeje.",
        "Hola 😊 ¿Sabías que ya llevamos {days} días? Qué padre.",
        "Holi. {days} días ya, ¿cómo estás hoy?",
    ],
}


class SessionManager:
    """
    Maneja el inicio y cierre de sesión de Sofía.
    """

    def __init__(self, db: Database):
        self.db = db

    # --------------------------------------------------------
    # AL ARRANCAR — generar saludo con memoria
    # --------------------------------------------------------

    def get_greeting(self, user_id: str) -> str:
        """
        Genera el saludo inicial según el historial del usuario.
        Prioridad:
          1. Días hablando (si son ≥ 3)
          2. Tema relevante de la última sesión
          3. Usuario conocido sin temas
          4. Usuario nuevo
        """
        session = self.db.load_last_session(user_id)

        if not session:
            return pick(SALUDOS["nuevo"])

        days = self._days_since(session["date"])
        session_count = session.get("session_count", 1)
        topics = session.get("topics", [])
        facts  = session.get("important_facts", {})

        # 1. Días hablando (≥ 3 sesiones)
        if session_count >= 3:
            frase = pick(SALUDOS["dias_hablando"])
            return frase.format(days=session_count)

        # 2. Tema relevante
        top_topic = self._pick_top_topic(topics, facts)
        if top_topic:
            frase = pick(SALUDOS["conocido_con_tema"])
            return frase.format(topic=top_topic)

        # 3. Conocido sin temas
        return pick(SALUDOS["conocido_sin_temas"])

    # --------------------------------------------------------
    # AL CERRAR — guardar resumen de sesión
    # --------------------------------------------------------

    def save_session(self, user_id: str, profile) -> None:
        """
        Guarda el resumen de la sesión actual.
        Llama esto cuando el usuario escribe 'salir' o el bot se cierra.
        """
        # Incrementar contador de sesiones
        last = self.db.load_last_session(user_id)
        session_count = (last["session_count"] + 1) if last else 1

        self.db.save_session(
            user_id=user_id,
            topics=profile.topics,
            important_facts=profile.important_facts,
            session_count=session_count
        )

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------

    def _days_since(self, date: datetime) -> int:
        """Días desde la última sesión."""
        delta = datetime.now() - date
        return max(0, delta.days)

    def _pick_top_topic(self, topics: list, facts: dict) -> Optional[str]:
        """
        Elige el tema más relevante para mencionar.
        Prioriza hechos con peso alto, luego topics.
        Filtra palabras genéricas que no aportan contexto.
        """
        stopwords = {
            "hola", "bien", "mal", "nada", "algo", "todo",
            "eso", "esto", "aqui", "ahi", "igual", "bueno"
        }

        # Primero buscar en important_facts (más ricos en contexto)
        if facts:
            # Ordenar por peso descendente
            sorted_facts = sorted(facts.items(), key=lambda x: x[1], reverse=True)
            for fact, weight in sorted_facts:
                if weight >= 2.0:
                    # Limpiar el hecho para que suene natural
                    # "le gusta el fútbol" → "el fútbol"
                    clean = self._clean_fact(fact)
                    if clean:
                        return clean

        # Luego topics
        for topic in topics:
            if topic.lower() not in stopwords and len(topic) > 3:
                return topic

        return None

    def _clean_fact(self, fact: str) -> str:
        """
        Convierte un hecho guardado en algo natural para mencionar.
        'le gusta futbol' → 'el fútbol'
        'estudia medicina' → 'la medicina'
        'soy estudiante' → None (demasiado genérico)
        """
        skip_patterns = ["soy ", "tiene ", "es "]
        fact_lower = fact.lower()

        for pattern in skip_patterns:
            if fact_lower.startswith(pattern):
                return ""

        # "le gusta X" → "X"
        if "gusta" in fact_lower:
            parts = fact_lower.split("gusta")
            if len(parts) > 1:
                topic = parts[1].strip()
                return topic if len(topic) > 2 else ""

        # "estudia X" → "X"
        if "estudia" in fact_lower:
            parts = fact_lower.split("estudia")
            if len(parts) > 1:
                return parts[1].strip()

        # "trabaja en X" → "X"
        if "trabaja" in fact_lower:
            parts = fact_lower.split("en")
            if len(parts) > 1:
                return parts[-1].strip()

        return fact