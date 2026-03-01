# core/response_enricher.py
# ============================================================
# ResponseEnricher — enriquecimiento post-generación.
# v0.13.1: recibe UserSession en vez de diccionarios separados.
# ============================================================

import random
from config.sofia_voice import (
    CURIOSITY_QUESTIONS, MOMENTUM_DEPTH_PROMPTS,
    QUOTE_RECALL_PHRASES, pick,
    sofia_self_share, sofia_reaction_with_self,
)
from config import settings


class ResponseEnricher:

    def __init__(self, semantic_memory, topic_lock):
        self.semantic_memory = semantic_memory
        self.topic_lock      = topic_lock

    def enrich(self, response: str, session, user_id: str,
               active_topic, streak: int, message: str,
               sentiment: float, emotion, keywords: list,
               context: dict, traits: dict,
               important_quotes: list = None, emotion_engine=None,
               msg_n: int = 0, profile=None) -> str:

        has_question     = "?" in response
        usuario_negativo = sentiment is not None and sentiment < -0.2

        # ── Streak de mensajes cortos ────────────────────────
        if streak >= settings.SHORT_RESPONSE_STREAK_MAX:
            cooldown = getattr(settings, "COOLDOWN_CURIOSITY_Q", 4)
            if session.cooldown_ok("momentum", msg_n, cooldown):
                session.mark_cooldown("momentum", msg_n)
                return pick(MOMENTUM_DEPTH_PROMPTS)
            return response

        if has_question:
            return response

        # ── Memoria semántica ────────────────────────────────
        semantic_cooldown = getattr(settings, "COOLDOWN_SEMANTIC_RECALL", 6)
        semantic_facts    = getattr(profile, "semantic_facts", {}) if profile else {}
        if (
            semantic_facts
            and emotion.trust > 50
            and session.cooldown_ok("semantic", msg_n, semantic_cooldown)
            and random.random() < 0.20
        ):
            key          = random.choice(list(semantic_facts.keys()))
            val          = semantic_facts[key]
            fact_natural = self.semantic_memory._fact_to_human(key, val)
            if fact_natural:
                session.mark_cooldown("semantic", msg_n)
                return f"{response} {random.choice([f'Oye, recuerdo que {fact_natural}. ¿Cómo va eso?', f'A propósito… {fact_natural}, ¿verdad? jeje', f'Mm, recuerdo que {fact_natural}.'])}"

        # ── Quote recall ─────────────────────────────────────
        quote_cooldown = getattr(settings, "COOLDOWN_QUOTE_RECALL", 8)
        if (
            important_quotes
            and emotion.trust > 60
            and session.cooldown_ok("quote", msg_n, quote_cooldown)
            and random.random() < settings.QUOTE_RECALL_PROB
        ):
            quote = random.choice(important_quotes)
            frase = random.choice(QUOTE_RECALL_PHRASES).format(quote=quote)
            session.mark_cooldown("quote", msg_n)
            return f"{response} {frase}"

        # ── Topic lock activo ────────────────────────────────
        if active_topic and not usuario_negativo and sentiment is not None and abs(sentiment) <= 0.4:
            history = session.topic_question_history
            tq = self.topic_lock.get_topic_question(active_topic, history)
            if tq:
                history.append(tq)
                session.topic_question_history = history[-5:]
                return f"{response} {tq}"

        persona_cooldown   = getattr(settings, "COOLDOWN_PERSONA_SHARE", 5)
        curiosity_cooldown = getattr(settings, "COOLDOWN_CURIOSITY_Q", 4)

        # ── Sofia comparte algo de sí misma ──────────────────
        if (
            not usuario_negativo
            and "?" not in message
            and sentiment is not None and sentiment >= 0
            and emotion.trust >= settings.CURIOSITY_TRUST_MIN
            and session.cooldown_ok("persona", msg_n, persona_cooldown)
            and random.random() < 0.35
        ):
            session.mark_cooldown("persona", msg_n)
            share = sofia_self_share(emotion.trust, session.msg_counter)
            return f"{response} {share}"

        # ── Pregunta de curiosidad contextual ────────────────
        elif (
            not usuario_negativo
            and "?" not in message
            and sentiment is not None and sentiment >= -0.1
            and emotion.trust >= settings.CURIOSITY_TRUST_MIN
            and traits.get("curiosity", 50) > 50
            and session.cooldown_ok("curiosity", msg_n, curiosity_cooldown)
            and random.random() < settings.CURIOSITY_TRIGGER_PROB
        ):
            question = self._contextual_question(keywords, sentiment, context, emotion)
            session.mark_cooldown("curiosity", msg_n)
            return f"{response} {question}"

        return response

    @staticmethod
    def _contextual_question(keywords, sentiment, context, emotion=None) -> str:
        if emotion and random.random() < getattr(settings, "SOFIA_REACTION_PROB", 0.25):
            return sofia_reaction_with_self(emotion.primary_emotion.value if emotion else "neutral")
        if sentiment > 0.5:
            return pick(["¿Eso te hizo feliz de verdad?", "Oye, ¿cómo te sentiste con eso?", "¿Eso lo esperabas o fue sorpresa?"])
        if sentiment < -0.3:
            return pick(["¿Estás bien?", "¿Cómo te dejó eso?", "¿Pudiste hablarlo con alguien?"])
        if context.get("repetition_level", 0) > 0:
            return pick(["¿Qué quieres realmente decirme?", "¿Hay algo más detrás de eso?", "Mm… siento que hay algo que no me estás diciendo."])
        return pick(CURIOSITY_QUESTIONS)