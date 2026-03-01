# core/decision_engine.py
# ============================================================
# SocialBot v0.13.1
# CAMBIOS vs v0.13.0:
#   - STATELESS: los 11 diccionarios de estado por usuario se
#     extrajeron a models/user_session.py + core/session_store.py
#   - El engine ya no tiene estado mutable propio.
#   - Cada request: get(session) → procesar → save(session)
#   - Compatible con múltiples workers y Redis en el futuro.
#   - MANTIENE: toda la lógica de prioridades de v0.13.0 intacta.
# ============================================================

import unicodedata as _uc
from datetime import datetime
from typing import Dict, Any, Optional
import random

from models.state import EmotionalState
from models.interaction import Interaction
from models.user_session import UserSession
from core.memory import Memory
from core.tool_engine import ToolEngine
from core.session_store import SessionStore
from core.semantic_memory import SemanticMemory, IntentClassifier
from core.context_analyzer import ContextAnalyzer
from core.response_builder import ResponseBuilder
from core.llm_response_builder import LLMResponseBuilder
from core.response_enricher import ResponseEnricher
from core.handlers.confession_handler import ConfessionHandler
from core.handlers.aggression_handler import AggressionHandler
from utils.text_analyzer import TextAnalyzer
from utils.aggression_detector import AggressionDetector
from config import settings
from config.sofia_voice import (
    micro_expresion_v2, apply_verbosity, pick,
    detect_identity_question,
    REPEAT_RESPONSES,
    get_opinion,
    detect_direct_question,
    is_cuentame_trigger,
    _topic_lock,
    get_sofia_thought,
    trust_level,
)


class DecisionEngine:

    def __init__(self, session_store: SessionStore = None):
        self.analyzer            = TextAnalyzer()
        self.aggression_detector = AggressionDetector()
        self.topic_lock          = _topic_lock
        self.semantic_memory     = SemanticMemory()
        self.intent_classifier   = IntentClassifier(self.semantic_memory)
        self.tool_engine         = ToolEngine()

        # Store externo — swappeable por Redis sin tocar el engine
        self.session_store = session_store or SessionStore()

        self.thresholds = {
            "ignore":         -0.2,
            "reveal_secret":  95,
            "hostile_energy": 30,
        }

        self.context_analyzer  = ContextAnalyzer(self.analyzer)
        self.response_builder  = LLMResponseBuilder()
        self.response_enricher = ResponseEnricher(
            semantic_memory = self.semantic_memory,
            topic_lock      = self.topic_lock,
        )

    # ============================================================
    # MÉTODO PRINCIPAL
    # ============================================================

    async def decide_response(
        self,
        user_id: str,
        message: str,
        emotion: EmotionalState,
        memory: Memory,
        profile_modifiers: Optional[dict] = None,
        display_name: str = "tú",
        emotion_engine=None,
        profile_manager=None,
        profile=None,
    ) -> Dict[str, Any]:

        if profile_modifiers is None:
            profile_modifiers = {}

        # ── Obtener sesión del usuario ───────────────────────
        session = self.session_store.get(user_id)
        session.msg_counter += 1
        msg_n = session.msg_counter

        # ── Extracción de hechos semánticos ─────────────────
        if profile is not None:
            new_facts = self.semantic_memory.extract_facts(message)
            if new_facts:
                existing = getattr(profile, "semantic_facts", {}) or {}
                existing.update(new_facts)
                max_facts = getattr(settings, "SEMANTIC_FACTS_MAX", 20)
                if len(existing) > max_facts:
                    keys_to_remove = list(existing.keys())[:(len(existing) - max_facts)]
                    for k in keys_to_remove:
                        del existing[k]
                profile.semantic_facts = existing

        name      = display_name
        sentiment = self.analyzer.analyze_sentiment(message)
        keywords  = self.analyzer.extract_keywords(message)
        is_humor  = self.analyzer.is_humor(message)

        avg_sentiment    = memory.get_average_sentiment_for(user_id)
        last_interaction = memory.get_last_interaction_with(user_id)
        recency_bonus    = (
            last_interaction.sentiment * 0.3
            if last_interaction and last_interaction.sentiment is not None
            else 0
        )
        relationship_score = avg_sentiment * 0.5 + recency_bonus

        traits            = profile_modifiers.get("effective_traits", {})
        important_facts   = profile_modifiers.get("important_facts", {})
        important_quotes  = profile_modifiers.get("important_quotes", [])
        patience          = profile_modifiers.get("patience", 1.0)
        ignore_adjust     = profile_modifiers.get("ignore_threshold_adjust", 0.0)
        ignore_threshold  = self.thresholds["ignore"] * patience + ignore_adjust
        hostile_threshold = profile_modifiers.get("hostility_threshold", self.thresholds["hostile_energy"])
        empathy_bonus     = profile_modifiers.get("empathy_bonus", 0.0)

        is_apology = self.analyzer.is_apology(message)

        if settings.SECRETS_DAILY_RESET:
            session.daily_secrets_reset_if_needed()

        # ── Short streak ─────────────────────────────────────
        SHORT_TOKENS = {
            "ok", "bien", "si", "no", "sí", "mm", "k", "va",
            "ya", "dale", "sale", "claro", "bueno", "pos", "pues"
        }
        msg_clean = message.strip().lower()
        if len(msg_clean) < 10 or msg_clean in SHORT_TOKENS:
            session.short_streak += 1
        else:
            session.short_streak = 0
        streak = session.short_streak

        if session.has_active_conflict:
            streak = 0

        agg_count  = session.aggression_count
        rec_needed = session.recovery_needed

        # ════════════════════════════════════════════════════
        # PRIORITY RESOLVER
        # ════════════════════════════════════════════════════

        # PRIORIDAD 0.5 — Memory check
        intent = self.intent_classifier.classify(message)
        if intent == "memory_check":
            session.last_message = message
            session.repeat_count = 0
            semantic_facts = getattr(profile, "semantic_facts", {}) if profile else {}
            recall_resp    = self.semantic_memory.build_recall_response(semantic_facts, name)
            if recall_resp is None:
                recall_resp = random.choice([
                    f"Mm… la verdad no tengo nada guardado de ti todavía, {name}. Cuéntame algo.",
                    f"No recuerdo nada concreto aún. ¿Quieres que empiece a conocerte?",
                    f"Todavía estoy aprendiendo quién eres, {name}. Dime algo sobre ti.",
                ])
            night_comment = self._get_night_comment_if_due(session, msg_n, emotion.trust, name, emotion_engine)
            if night_comment:
                recall_resp = f"{recall_resp} {night_comment}"
            self.session_store.save(user_id, session)
            return self._return(user_id, message, sentiment, recall_resp,
                                emotion, relationship_score, action="memory_check")

        # PRIORIDAD 0.7 — Confesión emocional
        if ConfessionHandler.is_confession(message):
            self.topic_lock.release(user_id)
            session.reset_conflict()
            agg_count  = 0
            rec_needed = 0
            conf_resp  = ConfessionHandler.get_confession_response(trust_level(emotion.trust), name)
            session.last_message        = message
            session.repeat_count        = 0
            session.last_was_confession = True
            self.session_store.save(user_id, session)
            return self._return(user_id, message, sentiment, conf_resp,
                                emotion, relationship_score, action="respond")

        # PRIORIDAD 0.8 — Introspección emocional
        _norm = self._norm_msg(message)
        if ConfessionHandler.is_introspection_question(message, _norm) and not (is_apology and agg_count > 0):
            session.last_message = message
            session.repeat_count = 0
            dmg = getattr(profile, "relationship_damage", 0.0) if profile else 0.0
            if ConfessionHandler.is_did_i_hurt(_norm) and profile is not None and dmg < 2.0:
                resp = ConfessionHandler.get_did_i_hurt_response()
                self.session_store.save(user_id, session)
                return self._return(user_id, message, sentiment, resp,
                                    emotion, relationship_score, action="respond")
            resp = ConfessionHandler.build_introspection_response(emotion, name, relationship_damage=dmg)
            self.session_store.save(user_id, session)
            return self._return(user_id, message, sentiment, resp,
                                emotion, relationship_score, action="introspection")

        # PRIORIDAD 1 — Identidad
        # FIX v0.13.2: emotion.tone es stale aquí — el registry aún no actualizó
        # el objeto emotion. Se lee de get_registry(user_id).tone directamente.
        # FIX v0.13.2: emotion_engine.state.tone puede ser None si el registry
        # aún no procesó este user. Se garantiza que siempre sea un string válido.
        _tone_for_identity = (
            (emotion_engine.state.tone or "neutral")
            if emotion_engine and hasattr(emotion_engine, "state") and emotion_engine.state
            else getattr(emotion, "tone", None)
        ) or "neutral"
        identity_response = detect_identity_question(message, tone=_tone_for_identity)
        if identity_response:
            _is_how_are_you = any(k in _norm for k in [
                "como estas", "como te sientes", "todo bien", "estas bien",
                "que tal estas", "como vas", "como amaneciste", "que tal sofia",
            ])
            _has_real_state = (
                emotion.primary_emotion.value in ("sad", "angry", "fearful")
                or (getattr(profile, "relationship_damage", 0.0) >= 3.0)
                or emotion.energy < 25
            )
            if _is_how_are_you and _has_real_state:
                dmg  = getattr(profile, "relationship_damage", 0.0) if profile else 0.0
                resp = ConfessionHandler.build_introspection_response(emotion, name, relationship_damage=dmg)
                session.last_message = message
                session.repeat_count = 0
                self.session_store.save(user_id, session)
                return self._return(user_id, message, sentiment, resp,
                                    emotion, relationship_score, action="introspection")
            session.last_message = message
            session.repeat_count = 0
            _resp_id = self._inject_name(identity_response, name)
            _micro   = micro_expresion_v2(emotion.energy, emotion.trust, getattr(emotion, "tone", "neutral"))
            if _micro and not _resp_id.startswith(_micro.strip()):
                if _micro.strip() in (".", "\u2026", "Mm."):
                    _resp_id = (_micro.strip() + " " + _resp_id).strip()
                else:
                    _resp_id = (_micro + _resp_id[0].lower() + _resp_id[1:]).strip()
            _resp_id = apply_verbosity(_resp_id, getattr(emotion, "verbosity", "medium"))
            self.session_store.save(user_id, session)
            return self._return(user_id, message, sentiment, _resp_id,
                                emotion, relationship_score, action="identity")

        # PRIORIDAD 1.5 — "Cuéntame algo"
        if is_cuentame_trigger(message):
            session.last_message = message
            session.repeat_count = 0
            self.session_store.save(user_id, session)
            return self._return(user_id, message, sentiment, get_sofia_thought(),
                                emotion, relationship_score, action="initiative")

        # PRIORIDAD 2 — Modo noche
        night_comment = self._get_night_comment_if_due(session, msg_n, emotion.trust, name, emotion_engine)

        # PRIORIDAD 3 — Ofensa activa
        aggression = self.aggression_detector.detect(message, trust=emotion.trust)
        if aggression["detected"]:
            if not aggression["is_joke"]:
                session.aggression_count += 1
                agg_count = session.aggression_count
                self.topic_lock.release(user_id)
            if agg_count == 4:
                session.recovery_needed = 1
                self.session_store.save(user_id, session)
                return self._return(user_id, message, sentiment, "…",
                                    emotion, relationship_score, action="silence")
            response = AggressionHandler.escalation_response(agg_count, aggression["level"], aggression["is_joke"])
            action   = "limit" if agg_count >= 5 else "boundary"
            self.session_store.save(user_id, session)
            return self._return(user_id, message, sentiment, response,
                                emotion, relationship_score, action=action)

        # PRIORIDAD 4 — Recovery activo
        _damage             = getattr(profile, 'relationship_damage', 0.0) if profile else 0.0
        _recovery_by_damage = is_apology and _damage >= 2.0 and agg_count == 0
        if is_apology and (agg_count > 0 or _recovery_by_damage):
            if rec_needed == 0:
                session.recovery_needed = getattr(settings, "RECOVERY_MESSAGES_REQUIRED", 3)
                rec_needed = session.recovery_needed
            response = AggressionHandler.recovery_response(rec_needed)
            session.recovery_needed = max(0, rec_needed - 1)
            if session.recovery_needed == 0:
                session.aggression_count = 0
            response = self._apply_micro(response, emotion, tone="neutral")
            self.session_store.save(user_id, session)
            return self._return(user_id, message, sentiment, response,
                                emotion, relationship_score, action="recovery")

        # ── Retractaciones y recovery pasivo ─────────────────
        _RETRACTION_PHRASES = [
            "era broma", "fue broma", "es broma", "estaba bromeando",
            "solo bromeaba", "solo era broma", "bromea", "estoy bien",
            "todo bien", "no te preocupes", "no era en serio",
        ]
        _is_retraction       = any(p in _norm for p in _RETRACTION_PHRASES)
        _post_retraction     = False
        _prev_was_confession = session.last_was_confession
        session.last_was_confession = False

        if _is_retraction and rec_needed > 0:
            session.reset_conflict()
            agg_count        = 0
            rec_needed       = 0
            _post_retraction = True
        elif _is_retraction and _prev_was_confession:
            _post_retraction = True
        elif (
            rec_needed > 0
            and sentiment is not None and sentiment >= 0
            and not ConfessionHandler.is_confession(message)
            and not ConfessionHandler.is_introspection_question(message, _norm)
        ):
            _AFFECTION = ["te quiero", "te amo", "te adoro", "me gustas", "me caes"]
            _APOLOGY   = ["perdon", "lo siento", "disculpa", "fue mi culpa", "me arrepiento", "estuvo mal"]
            _is_pp     = (
                agg_count > 0
                and any(m in _norm for m in _AFFECTION)
                and not any(m in _norm for m in _APOLOGY)
            )
            if _is_pp:
                _SKEPTICAL = [
                    "Mm… ya lo sé. Pero después de lo que pasó, necesito más que palabras.",
                    "Mm… te escucho. Aunque cuesta creerlo cuando todo sube y baja así.",
                    "Eso ya lo dijiste. ¿De verdad lo sientes?",
                    "Mm… no sé qué pensar cuando el calor y el frío vienen juntos así.",
                ]
                response = self._apply_micro(random.choice(_SKEPTICAL), emotion, tone="slightly_cold")
                self.session_store.save(user_id, session)
                return self._return(user_id, message, sentiment, response,
                                    emotion, relationship_score, action="recovery")
            response = AggressionHandler.recovery_response(rec_needed)
            session.recovery_needed = max(0, rec_needed - 1)
            if session.recovery_needed == 0:
                session.aggression_count = 0
            response = self._apply_micro(response, emotion, tone="neutral")
            self.session_store.save(user_id, session)
            return self._return(user_id, message, sentiment, response,
                                emotion, relationship_score, action="recovery")

        # PRIORIDAD 4.5 — Pregunta directa
        direct_answer = detect_direct_question(message)
        if direct_answer:
            session.last_message = message
            session.repeat_count = 0
            if random.random() < 0.4:
                direct_answer += random.choice([
                    " ¿Algo más que quieras saber?", " ¿Te sirve eso?",
                    " ¿Hay algo más?", " ¿Eso era lo que buscabas?",
                ])
            self.session_store.save(user_id, session)
            return self._return(user_id, message, sentiment, direct_answer,
                                emotion, relationship_score, action="direct_answer")

        # PRIORIDAD 4.6 — Búsqueda web
        _is_explicit_search = self.tool_engine.is_explicit_search(message)
        _search_ok = _is_explicit_search or session.cooldown_ok("web_search", msg_n, getattr(settings, "SEARCH_COOLDOWN", 3))
        if (
            agg_count == 0 and rec_needed == 0
            and getattr(settings, "TOOLS_ENABLED", True)
            and getattr(settings, "SEARCH_ENABLED", True)
            and _search_ok
            and self.tool_engine.should_search(message)
        ):
            raw = await self.tool_engine.search(message)
            search_response = self.tool_engine.wrap_result(
                raw_result=raw or "", message=message,
                energy=emotion.energy, trust=emotion.trust,
                emotion=emotion.primary_emotion.value,
            )
            session.mark_cooldown("web_search", msg_n)
            session.last_message = message
            session.repeat_count = 0
            self.session_store.save(user_id, session)
            return self._return(user_id, message, sentiment, search_response,
                                emotion, relationship_score, action="web_search")

        # PRIORIDAD 4.7 — Anti-repetición
        last_norm = self._norm_msg(session.last_message)
        if _norm == last_norm and _norm:
            session.repeat_count += 1
            repeat_resp = pick(REPEAT_RESPONSES[min(session.repeat_count, 3)])
            session.last_message = message
            self.session_store.save(user_id, session)
            return self._return(user_id, message, sentiment, repeat_resp,
                                emotion, relationship_score, action="repeat")
        else:
            session.last_message = message
            session.repeat_count = 0

        # PRIORIDAD 5 — Opinión / tema
        if agg_count == 0 and rec_needed == 0:
            opinion = get_opinion(message, name, user_id)
            if opinion:
                self.session_store.save(user_id, session)
                return self._return(user_id, message, sentiment, opinion,
                                    emotion, relationship_score, action="opinion")

        # PRIORIDAD 6 — Topic activo
        active_topic = self.topic_lock.get_active(user_id)

        # PRIORIDAD 7 — Acción principal
        action          = "respond"
        special_content = None
        secret_blocked  = rec_needed > 0 or agg_count > 0

        if sentiment is not None and relationship_score < ignore_threshold and sentiment < -0.3:
            action = "ignore"
        elif emotion.energy < hostile_threshold and sentiment is not None and sentiment < -0.2:
            action = "hostile_response"
        elif emotion.trust > self.thresholds["reveal_secret"] and not secret_blocked:
            if session.secrets_revealed < 2:
                action               = "reveal_secret"
                special_content      = ResponseBuilder.get_secret()
                session.secrets_revealed += 1
            else:
                action = "respond"

        recent_interactions = await memory.get_recent_interactions(user_id, limit=3)
        context = self.context_analyzer.analyze(
            current_message     = message,
            current_sentiment   = sentiment,
            recent_interactions = recent_interactions,
            current_keywords    = keywords,
        )

        eff_emotion = ContextAnalyzer.effective_emotion(emotion, agg_count, rec_needed, sentiment)
        response    = await self.response_builder.generate(
            action            = action,
            emotion           = eff_emotion,
            special_content   = special_content,
            important_facts   = important_facts if rec_needed == 0 else {},
            context           = context,
            traits            = traits,
            empathy_bonus     = empathy_bonus,
            relationship_score= relationship_score,
            name              = name,
            is_humor          = is_humor,
            user_id           = user_id,
            user_sentiment    = sentiment,
            tone_override     = "neutral" if _post_retraction else None,
            user_message      = message,
            memory            = memory,   # ← historial real de conversación
        )

        # PRIORIDAD 8 — Enriquecer (solo con plantillas, no con LLM)
        _usar_llm = getattr(self.response_builder, "is_llm", False)
        if action == "respond" and rec_needed == 0 and not _usar_llm:
            response = self.response_enricher.enrich(
                response         = response,
                session          = session,
                user_id          = user_id,
                active_topic     = active_topic,
                streak           = streak,
                message          = message,
                sentiment        = sentiment,
                emotion          = emotion,
                keywords         = keywords,
                context          = context,
                traits           = traits,
                important_quotes = important_quotes,
                emotion_engine   = emotion_engine,
                msg_n            = msg_n,
                profile          = profile,
            )

        # PRIORIDAD 9 — Decorador nocturno
        if night_comment and action in (
            "respond", "direct_answer", "initiative", "opinion",
            "memory_check", "web_search", "introspection"
        ):
            response = f"{response} {night_comment}"

        self.session_store.save(user_id, session)
        return self._return(user_id, message, sentiment, response,
                            emotion, relationship_score, action=action)

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _norm_msg(t: str) -> str:
        return _uc.normalize("NFD", t.strip().lower()).encode("ascii", "ignore").decode()

    @staticmethod
    def _inject_name(text: str, name: str) -> str:
        return text.replace("{name}", name)

    @staticmethod
    def _apply_micro(response: str, emotion, tone: str) -> str:
        verbosity = getattr(emotion, "verbosity", "medium")
        micro     = micro_expresion_v2(emotion.energy, emotion.trust, tone)
        if micro and not response.startswith(micro.strip()):
            if micro.strip() in (".", "\u2026", "Mm."):
                response = (micro.strip() + " " + response).strip()
            else:
                response = (micro + response[0].lower() + response[1:]).strip()
        return apply_verbosity(response, verbosity)

    def _get_night_comment_if_due(self, session: UserSession, msg_n: int,
                                   trust: float, name: str, emotion_engine) -> Optional[str]:
        if not (emotion_engine and emotion_engine.is_night_mode()):
            return None
        cooldown = getattr(settings, "COOLDOWN_NIGHT_COMMENT", 5)
        if not session.cooldown_ok("night", msg_n, cooldown):
            return None
        if random.random() >= 0.30:
            return None
        comment = self._night_comment(trust, name)
        session.mark_cooldown("night", msg_n)
        return comment

    def _night_comment(self, trust: float, name: str) -> Optional[str]:
        high = [
            f"Por cierto {name}… ya es tarde, ¿no deberías descansar?",
            "Oye, ¿no es muy tarde para estar despierto?",
            f"A esta hora las conversaciones se ponen raras, ¿verdad {name}? jeje",
            "Mm… ya es tarde. Pero aquí estoy.",
        ]
        mid = [
            "Por cierto, ya es tarde.",
            "Oye… ¿no deberías estar durmiendo?",
            "Mm… es hora rara para hablar jeje.",
            "Ya es noche, ¿todo bien?",
        ]
        return pick(high if trust > 70 else mid)

    def _return(self, user_id, message, sentiment, response, emotion,
                relationship_score, action="respond", emotion_after=None):
        interaction = Interaction(
            user_id        = user_id,
            message        = message,
            sentiment      = sentiment,
            response       = response,
            timestamp      = datetime.now(),
            emotion_before = emotion.primary_emotion.value,
            emotion_after  = emotion_after if emotion_after is not None else emotion.primary_emotion.value,
        )
        return {
            "action":             action,
            "response":           response,
            "interaction":        interaction,
            "relationship_score": relationship_score,
        }