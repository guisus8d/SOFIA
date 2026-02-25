# core/decision_engine.py
# ============================================================
# SocialBot v0.9.1
# CAMBIOS vs v0.9.0:
#   - FIX BUG CRÍTICO: TopicLock — ahora se importa la INSTANCIA global
#     (_topic_lock) de sofia_voice, no la clase. Antes se creaban dos
#     objetos separados: get_opinion() usaba uno y DecisionEngine otro,
#     provocando que el seguimiento de temas se desincronizara.
#   - FIX: eliminado self.topic_lock.update() duplicado en PRIORIDAD 5.
#     get_opinion() ya llama internamente a _topic_lock.update().
#   - MANTIENE: todo lo demás de v0.9.0
# ============================================================

from datetime import datetime, date
from typing import Dict, Any, Optional
from models.state import EmotionalState
from models.interaction import Interaction
from core.memory import Memory
from utils.text_analyzer import TextAnalyzer
from utils.aggression_detector import AggressionDetector
from config import settings
from config.sofia_voice import (
    RESPUESTAS, CONTEXTO, MARCA_PERSONAL,
    micro_expresion, trust_level, pick,
    detect_identity_question,
    ESCALATION_RESPONSES,
    RECOVERY_RESPONSES,
    CURIOSITY_QUESTIONS,
    MOMENTUM_DEPTH_PROMPTS,
    REPEAT_RESPONSES,
    get_opinion,
    OPINIONES,
    QUOTE_RECALL_PHRASES,
    NIGHT_RESPONSES,
    RESPUESTAS_NOCHE,
    detect_direct_question,
    get_sofia_thought,
    is_cuentame_trigger,
    _topic_lock,                   # FIX v0.9.1: instancia global, no la clase
    sofia_self_share,
    sofia_mood_expression,
    sofia_reaction_with_self,
)
import random
import time


# ============================================================
# SEMANTIC MEMORY v0.8.2
# ============================================================

class SemanticMemory:
    """
    Detecta y almacena hechos del tipo {tema: valor} a partir del texto.
    """

    EXTRACTION_RULES = [
        (["me gusta la pizza", "amo la pizza"],                       "comida_favorita",       "pizza"),
        (["me gustan los tacos", "amo los tacos"],                    "comida_favorita",       "tacos"),
        (["me gusta el sushi"],                                        "comida_favorita",       "sushi"),
        (["me gusta la hamburguesa", "me gustan las hamburguesas"],   "comida_favorita",       "hamburguesa"),
        (["me gusta el ramen"],                                        "comida_favorita",       "ramen"),
        (["me gusta el futbol", "me encanta el futbol"],              "deporte_interes",       "futbol"),
        (["no tengo equipo", "no tengo equipo de futbol"],            "futbol_tiene_equipo",   "no"),
        (["mi equipo es", "soy del"],                                  "futbol_equipo",          None),
        (["me gusta el basquetbol", "me gusta el basket"],            "deporte_interes",       "basquetbol"),
        (["me gusta la musica", "amo la musica"],                     "musica_le_gusta",       "si"),
        (["estudio", "soy estudiante"],                                "ocupacion",             "estudiante"),
        (["trabajo", "soy trabajador"],                                "ocupacion",             "trabajador"),
        (["estoy bien", "todo bien"],                                  "estado_general",        "bien"),
        (["estoy mal", "no estoy bien"],                               "estado_general",        "mal"),
    ]

    MEMORY_CHECK_TRIGGERS = [
        "recuerdas", "te acuerdas", "sabes algo de mi", "sabes algo sobre mi",
        "que sabes de mi", "qué sabes de mí", "recuerdas algo", "me conoces",
        "que recuerdas", "qué recuerdas", "acordas", "ya te dije",
        "te dije que", "te conte que", "te conté que",
    ]

    def __init__(self):
        pass

    def _normalize(self, text: str) -> str:
        import unicodedata
        nfkd = unicodedata.normalize("NFD", text)
        return nfkd.encode("ascii", "ignore").decode("utf-8").lower().strip()

    def is_memory_check(self, message: str) -> bool:
        msg = self._normalize(message)
        return any(trigger in msg for trigger in self.MEMORY_CHECK_TRIGGERS)

    def extract_facts(self, message: str) -> dict:
        msg = self._normalize(message)
        found = {}
        for triggers, key, fixed_value in self.EXTRACTION_RULES:
            for trigger in triggers:
                if trigger in msg:
                    if fixed_value is not None:
                        found[key] = fixed_value
                    else:
                        idx = msg.find(trigger)
                        rest = msg[idx + len(trigger):].strip().split()
                        if rest:
                            # FIX: captura hasta 3 palabras para nombres compuestos
                            found[key] = " ".join(rest[:3])
                    break
        return found

    def build_recall_response(self, semantic_facts: dict, name: str) -> str:
        if not semantic_facts:
            return None

        priority_keys = [
            "comida_favorita", "deporte_interes", "futbol_tiene_equipo",
            "futbol_equipo", "ocupacion", "musica_le_gusta", "estado_general",
        ]

        facts_text = []
        for key in priority_keys:
            val = semantic_facts.get(key)
            if val:
                fact = self._fact_to_human(key, val)
                if fact:
                    facts_text.append(fact)

        for key, val in semantic_facts.items():
            if key not in priority_keys:
                fact = self._fact_to_human(key, val)
                if fact:
                    facts_text.append(fact)

        if not facts_text:
            return None

        if len(facts_text) == 1:
            templates = [
                f"Sí, recuerdo que {facts_text[0]}. ¿Por qué lo preguntas?",
                f"Claro, sé que {facts_text[0]}. ¿Hay algo más que quieras que sepa?",
                f"Mm… sí. Recuerdo que {facts_text[0]}.",
            ]
        else:
            lista = ", ".join(facts_text[:-1]) + f" y {facts_text[-1]}"
            templates = [
                f"Bueno, recuerdo algunas cosas: {lista}. ¿Eso es lo que buscabas?",
                f"Sé que {lista}. No es mucho, pero es lo que tengo jeje.",
                f"Mm… {lista}. ¿Quieres contarme algo más?",
            ]

        return random.choice(templates)

    def _fact_to_human(self, key: str, val: str) -> str:
        mapping = {
            "comida_favorita":     f"te gusta {val}",
            "deporte_interes":     f"te interesa el {val}",
            "futbol_tiene_equipo": ("no tienes equipo de fútbol" if val == "no" else f"tienes equipo de fútbol: {val}"),
            "futbol_equipo":       f"eres del {val}",
            "ocupacion":           f"eres {val}",
            "musica_le_gusta":     "te gusta la música",
            "estado_general":      f"generalmente estás {val}",
        }
        return mapping.get(key, f"{key}: {val}")


# ============================================================
# INTENT CLASSIFIER v0.8.2
# ============================================================

class IntentClassifier:
    def __init__(self, semantic_memory: SemanticMemory):
        self.sem = semantic_memory

    def classify(self, message: str) -> str:
        if self.sem.is_memory_check(message):
            return "memory_check"
        return "normal"


# ============================================================
# DECISION ENGINE v0.9.1
# ============================================================

class DecisionEngine:

    def __init__(self):
        self.analyzer            = TextAnalyzer()
        self.aggression_detector = AggressionDetector()
        self.topic_lock          = _topic_lock   # FIX v0.9.1: instancia global compartida con get_opinion()
        self.semantic_memory     = SemanticMemory()
        self.intent_classifier   = IntentClassifier(self.semantic_memory)

        self.thresholds = {
            "ignore":         -0.2,
            "reveal_secret":  95,
            "hostile_energy": 30
        }

        self.secrets_revealed:  Dict[str, int]  = {}
        self._secrets_date:     Dict[str, date]  = {}
        self.aggression_count:  Dict[str, int]  = {}
        self.recovery_needed:   Dict[str, int]  = {}
        self.short_streak:      Dict[str, int]  = {}
        self._topic_question_history: Dict[str, list] = {}
        self._last_message:     Dict[str, str]  = {}
        self._repeat_count:     Dict[str, int]  = {}

        # Cooldown por tipo de output
        self._output_cooldowns: Dict[str, Dict[str, int]] = {}
        self._msg_counter:      Dict[str, int] = {}

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

        # ── Contador de mensajes por usuario ──
        msg_n = self._msg_counter.get(user_id, 0) + 1
        self._msg_counter[user_id] = msg_n

        # ── Extracción semántica ──
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

        agg_count  = self.aggression_count.get(user_id, 0)
        rec_needed = self.recovery_needed.get(user_id, 0)
        streak     = self.short_streak.get(user_id, 0)
        is_apology = self.analyzer.is_apology(message)

        if settings.SECRETS_DAILY_RESET:
            self._daily_secrets_reset(user_id)

        SHORT_TOKENS = {
            "ok", "bien", "si", "no", "sí", "mm", "k", "va",
            "ya", "dale", "sale", "claro", "bueno", "pos", "pues"
        }
        msg_clean = message.strip().lower()
        if len(msg_clean) < 10 or msg_clean in SHORT_TOKENS:
            self.short_streak[user_id] = streak + 1
        else:
            self.short_streak[user_id] = 0
        streak = self.short_streak[user_id]

        if agg_count > 0 or rec_needed > 0:
            streak = 0

        # ════════════════════════════════════════════════════
        # PRIORITY RESOLVER
        # ════════════════════════════════════════════════════

        # PRIORIDAD 0.5 — Memory check
        intent = self.intent_classifier.classify(message)
        if intent == "memory_check":
            self._last_message[user_id] = message
            self._repeat_count[user_id] = 0
            semantic_facts = getattr(profile, "semantic_facts", {}) if profile else {}
            recall_resp = self.semantic_memory.build_recall_response(semantic_facts, name)
            if recall_resp is None:
                no_memory_opts = [
                    f"Mm… la verdad no tengo nada guardado de ti todavía, {name}. Cuéntame algo.",
                    f"No recuerdo nada concreto aún. ¿Quieres que empiece a conocerte?",
                    f"Todavía estoy aprendiendo quién eres, {name}. Dime algo sobre ti.",
                ]
                recall_resp = random.choice(no_memory_opts)
            night_comment = self._get_night_comment_if_due(user_id, msg_n, emotion.trust, name, emotion_engine)
            if night_comment:
                recall_resp = f"{recall_resp} {night_comment}"
            return self._return(user_id, message, sentiment, recall_resp,
                                emotion, relationship_score, action="memory_check")

        # PRIORIDAD 1 — Identidad
        identity_response = detect_identity_question(message)
        if identity_response:
            self._last_message[user_id] = message
            self._repeat_count[user_id] = 0
            return self._return(user_id, message, sentiment,
                                self._inject_name(identity_response, name),
                                emotion, relationship_score, action="identity")

        # PRIORIDAD 1.5 — "Cuéntame algo"
        if is_cuentame_trigger(message):
            self._last_message[user_id] = message
            self._repeat_count[user_id] = 0
            thought = get_sofia_thought()
            return self._return(user_id, message, sentiment, thought,
                                emotion, relationship_score, action="initiative")

        # PRIORIDAD 2 — Modo noche (decorador con cooldown)
        night_comment = self._get_night_comment_if_due(user_id, msg_n, emotion.trust, name, emotion_engine)

        # PRIORIDAD 3 — Ofensa activa
        aggression = self.aggression_detector.detect(message, trust=emotion.trust)
        if aggression["detected"]:
            if not aggression["is_joke"]:
                agg_count += 1
                self.aggression_count[user_id] = agg_count
                self.topic_lock.release(user_id)

            if agg_count == 4:
                self.recovery_needed[user_id] = 1
                return self._return(user_id, message, sentiment, "…",
                                    emotion, relationship_score, action="silence")

            if agg_count >= 5:
                response = pick(ESCALATION_RESPONSES[5])
                return self._return(user_id, message, sentiment, response,
                                    emotion, relationship_score, action="limit")

            response = self._escalation_response(
                count=agg_count,
                level=aggression["level"],
                is_joke=aggression["is_joke"],
            )
            return self._return(user_id, message, sentiment, response,
                                emotion, relationship_score, action="boundary")

        # PRIORIDAD 4 — Recovery activo
        if is_apology and agg_count > 0:
            if rec_needed == 0:
                rec_needed = getattr(settings, "RECOVERY_MESSAGES_REQUIRED", 3)
                self.recovery_needed[user_id] = rec_needed

            response = self._recovery_response(rec_needed)
            rec_needed = max(0, rec_needed - 1)
            self.recovery_needed[user_id] = rec_needed
            if rec_needed == 0:
                self.aggression_count[user_id] = 0

            return self._return(user_id, message, sentiment, response,
                                emotion, relationship_score, action="recovery")

        if rec_needed > 0 and sentiment is not None and sentiment >= 0:
            rec_needed = max(0, rec_needed - 1)
            self.recovery_needed[user_id] = rec_needed
            if rec_needed == 0:
                self.aggression_count[user_id] = 0

        # PRIORIDAD 4.5 — Pregunta directa concreta
        direct_answer = detect_direct_question(message)
        if direct_answer:
            self._last_message[user_id] = message
            self._repeat_count[user_id] = 0
            if random.random() < 0.4:
                toques = [
                    " ¿Algo más que quieras saber?",
                    " ¿Te sirve eso?",
                    " ¿Hay algo más?",
                    " ¿Eso era lo que buscabas?",
                ]
                direct_answer += random.choice(toques)
            return self._return(user_id, message, sentiment, direct_answer,
                                emotion, relationship_score, action="direct_answer")

        # PRIORIDAD 4.7 — Anti-repetición inmediata
        import unicodedata as _uc_local
        def _norm_msg(t: str) -> str:
            return _uc_local.normalize("NFD", t.strip().lower()).encode("ascii", "ignore").decode()

        msg_norm  = _norm_msg(message)
        last_norm = _norm_msg(self._last_message.get(user_id, ""))

        if msg_norm == last_norm and msg_norm:
            rcount = self._repeat_count.get(user_id, 0) + 1
            self._repeat_count[user_id] = rcount
            level = min(rcount, 3)
            repeat_resp = pick(REPEAT_RESPONSES[level])
            self._last_message[user_id] = message
            return self._return(user_id, message, sentiment, repeat_resp,
                                emotion, relationship_score, action="repeat")
        else:
            self._last_message[user_id]  = message
            self._repeat_count[user_id]  = 0

        # PRIORIDAD 5 — Opinión / tema
        # FIX v0.9.1: eliminado self.topic_lock.update() duplicado.
        # get_opinion() ya llama internamente a _topic_lock.update().
        if agg_count == 0 and rec_needed == 0:
            opinion = get_opinion(message, name, user_id)
            if opinion:
                return self._return(user_id, message, sentiment, opinion,
                                    emotion, relationship_score, action="opinion")

        # PRIORIDAD 6 — Topic activo
        active_topic_result = self.topic_lock.update(user_id, message)
        active_topic = active_topic_result[0] if isinstance(active_topic_result, tuple) else active_topic_result

        # PRIORIDAD 7 — Acción principal
        action          = "respond"
        special_content = None
        secret_blocked  = rec_needed > 0 or agg_count > 0

        if sentiment is not None and relationship_score < ignore_threshold and sentiment < 0:
            action = "ignore"
        elif emotion.energy < hostile_threshold:
            action = "hostile_response"
        elif emotion.trust > self.thresholds["reveal_secret"] and not secret_blocked:
            secrets_today = self.secrets_revealed.get(user_id, 0)
            if secrets_today < 2:
                action = "reveal_secret"
                special_content = self._get_secret()
                self.secrets_revealed[user_id] = secrets_today + 1
            else:
                action = "respond"

        recent_interactions = await memory.get_recent_interactions(user_id, limit=3)
        context = self._analyze_conversation_context(
            current_message=message,
            current_sentiment=sentiment,
            recent_interactions=recent_interactions,
            current_keywords=keywords
        )

        facts_to_use = important_facts if rec_needed == 0 else {}

        response = self._generate_response(
            action=action,
            emotion=emotion,
            special_content=special_content,
            important_facts=facts_to_use,
            context=context,
            traits=traits,
            empathy_bonus=empathy_bonus,
            relationship_score=relationship_score,
            name=name,
            is_humor=is_humor,
            user_id=user_id,
        )

        # PRIORIDAD 8 — Enriquecer
        if action == "respond" and rec_needed == 0:
            response = self._enrich_response(
                response=response,
                user_id=user_id,
                active_topic=active_topic,
                streak=streak,
                message=message,
                sentiment=sentiment,
                emotion=emotion,
                keywords=keywords,
                context=context,
                traits=traits,
                important_quotes=important_quotes,
                emotion_engine=emotion_engine,
                msg_n=msg_n,
                profile=profile,
            )

        # PRIORIDAD 9 — Decorador nocturno
        if night_comment and action in ("respond", "direct_answer", "initiative", "opinion", "memory_check"):
            response = f"{response} {night_comment}"

        return self._return(user_id, message, sentiment, response,
                            emotion, relationship_score, action=action)

    # ============================================================
    # ENRIQUECIMIENTO v0.9.0
    # ============================================================

    def _enrich_response(
        self,
        response: str,
        user_id: str,
        active_topic: Optional[str],
        streak: int,
        message: str,
        sentiment: float,
        emotion: EmotionalState,
        keywords: list,
        context: dict,
        traits: dict,
        important_quotes: list = None,
        emotion_engine=None,
        msg_n: int = 0,
        profile=None,
    ) -> str:
        has_question = "?" in response

        # 7a — Momentum
        if streak >= settings.SHORT_RESPONSE_STREAK_MAX:
            return pick(MOMENTUM_DEPTH_PROMPTS)

        if has_question:
            return response

        # 7b — Recall semántico
        semantic_cooldown = getattr(settings, "COOLDOWN_SEMANTIC_RECALL", 6)
        semantic_facts = getattr(profile, "semantic_facts", {}) if profile else {}
        if (
            semantic_facts
            and emotion.trust > 50
            and self._cooldown_ok(user_id, "semantic", msg_n, semantic_cooldown)
            and random.random() < 0.20
        ):
            key = random.choice(list(semantic_facts.keys()))
            val = semantic_facts[key]
            fact_natural = self.semantic_memory._fact_to_human(key, val)
            if fact_natural:
                semantic_inserts = [
                    f"Oye, recuerdo que {fact_natural}. ¿Cómo va eso?",
                    f"A propósito… {fact_natural}, ¿verdad? jeje",
                    f"Mm, recuerdo que {fact_natural}.",
                ]
                self._mark_cooldown(user_id, "semantic", msg_n)
                return f"{response} {random.choice(semantic_inserts)}"

        # 7c — Quote recall
        quote_cooldown = getattr(settings, "COOLDOWN_QUOTE_RECALL", 8)
        if (
            important_quotes
            and emotion.trust > 60
            and self._cooldown_ok(user_id, "quote", msg_n, quote_cooldown)
            and random.random() < settings.QUOTE_RECALL_PROB
        ):
            quote = random.choice(important_quotes)
            frase = random.choice(QUOTE_RECALL_PHRASES).format(quote=quote)
            self._mark_cooldown(user_id, "quote", msg_n)
            return f"{response} {frase}"

        # 7d — Topic activo
        if active_topic:
            history = self._topic_question_history.get(user_id, [])
            tq = self.topic_lock.get_topic_question(active_topic, history)
            if tq:
                history.append(tq)
                self._topic_question_history[user_id] = history[-5:]
                return f"{response} {tq}"

        # ─────────────────────────────────────────────────────────────
        # 7e — PERSONALIDAD VIVA (v0.9.0)
        # Sofía alterna entre compartir algo de sí misma y hacer preguntas.
        # ─────────────────────────────────────────────────────────────
        persona_cooldown   = getattr(settings, "COOLDOWN_PERSONA_SHARE", 5)
        curiosity_cooldown = getattr(settings, "COOLDOWN_CURIOSITY_Q", 4)

        if (
            "?" not in message
            and sentiment is not None and sentiment >= 0
            and emotion.trust >= settings.CURIOSITY_TRUST_MIN
            and self._cooldown_ok(user_id, "persona", msg_n, persona_cooldown)
            and random.random() < 0.35
        ):
            self._mark_cooldown(user_id, "persona", msg_n)
            msg_count = self._msg_counter.get(user_id, 0)
            share = sofia_self_share(emotion.trust, msg_count)
            return f"{response} {share}"

        elif (
            "?" not in message
            and sentiment is not None and sentiment >= -0.1
            and emotion.trust >= settings.CURIOSITY_TRUST_MIN
            and traits.get("curiosity", 50) > 50
            and self._cooldown_ok(user_id, "curiosity", msg_n, curiosity_cooldown)
            and random.random() < settings.CURIOSITY_TRIGGER_PROB
        ):
            question = self._contextual_question(keywords, sentiment, context, emotion)
            self._mark_cooldown(user_id, "curiosity", msg_n)
            return f"{response} {question}"

        return response

    # ============================================================
    # HELPERS
    # ============================================================

    def _inject_name(self, text: str, name: str) -> str:
        return text.replace("{name}", name)

    def _cooldown_ok(self, user_id: str, output_type: str, current_msg_n: int, min_gap: int) -> bool:
        cd = self._output_cooldowns.setdefault(user_id, {})
        last_used = cd.get(output_type, -999)
        return (current_msg_n - last_used) >= min_gap

    def _mark_cooldown(self, user_id: str, output_type: str, current_msg_n: int):
        self._output_cooldowns.setdefault(user_id, {})[output_type] = current_msg_n

    def _get_night_comment_if_due(
        self, user_id: str, msg_n: int, trust: float, name: str, emotion_engine
    ) -> Optional[str]:
        if not (emotion_engine and emotion_engine.is_night_mode()):
            return None
        cooldown = getattr(settings, "COOLDOWN_NIGHT_COMMENT", 5)
        if not self._cooldown_ok(user_id, "night", msg_n, cooldown):
            return None
        if random.random() >= 0.30:
            return None
        comment = self._night_comment(trust, name)
        self._mark_cooldown(user_id, "night", msg_n)
        return comment

    def _night_comment(self, trust: float, name: str) -> Optional[str]:
        trust_high = trust > 70
        comentarios_high = [
            f"Por cierto {name}… ya es tarde, ¿no deberías descansar?",
            "Oye, ¿no es muy tarde para estar despierto?",
            f"A esta hora las conversaciones se ponen raras, ¿verdad {name}? jeje",
            "Mm… ya es tarde. Pero aquí estoy.",
        ]
        comentarios_mid = [
            "Por cierto, ya es tarde.",
            "Oye… ¿no deberías estar durmiendo?",
            "Mm… es hora rara para hablar jeje.",
            "Ya es noche, ¿todo bien?",
        ]
        opciones = comentarios_high if trust_high else comentarios_mid
        return pick(opciones)

    def _daily_secrets_reset(self, user_id: str):
        today = date.today()
        last_date = self._secrets_date.get(user_id)
        if last_date != today:
            self.secrets_revealed[user_id] = 0
            self._secrets_date[user_id] = today

    def _return(
        self,
        user_id: str,
        message: str,
        sentiment: float,
        response: str,
        emotion: EmotionalState,
        relationship_score: float,
        action: str = "respond"
    ) -> Dict[str, Any]:
        interaction = Interaction(
            user_id=user_id,
            message=message,
            sentiment=sentiment,
            response=response,
            timestamp=datetime.now(),
            emotion_before=emotion.primary_emotion.value,
            emotion_after=emotion.primary_emotion.value
        )
        return {
            "action": action,
            "response": response,
            "interaction": interaction,
            "relationship_score": relationship_score
        }

    # ============================================================
    # ESCALADA Y RECUPERACIÓN
    # ============================================================

    def _escalation_response(self, count: int, level: str, is_joke: bool) -> str:
        if is_joke:
            return pick([
                "Oye jeje… eso igual no suena bonito.",
                "Mm… aunque sea broma, cuida cómo lo dices.",
                "Jeje, pero eso igual me suena feo.",
            ])
        capped = max(min(count, 5), 3 if level == "alto" else 1)
        return pick(ESCALATION_RESPONSES[capped])

    def _recovery_response(self, recovery_needed: int) -> str:
        if recovery_needed >= 3:
            return pick(RECOVERY_RESPONSES["phase_1"])
        elif recovery_needed == 2:
            return pick(RECOVERY_RESPONSES["phase_2"])
        else:
            return pick(RECOVERY_RESPONSES["phase_3"])

    def _contextual_question(
        self,
        keywords: list,
        sentiment: float,
        context: dict,
        emotion: EmotionalState = None,
    ) -> str:
        # NUEVO v0.9.0: reacciones con algo de Sofía misma
        if emotion and random.random() < getattr(settings, "SOFIA_REACTION_PROB", 0.25):
            emo_val = emotion.primary_emotion.value if emotion else "neutral"
            return sofia_reaction_with_self(emo_val)

        if sentiment > 0.5:
            return pick([
                "¿Eso te hizo feliz de verdad?",
                "Oye, ¿cómo te sentiste con eso?",
                "¿Eso lo esperabas o fue sorpresa?",
            ])
        if sentiment < -0.3:
            return pick([
                "¿Estás bien?",
                "¿Cómo te dejó eso?",
                "¿Pudiste hablarlo con alguien?",
            ])
        if context.get("repetition_level", 0) > 0:
            return pick([
                "¿Qué quieres realmente decirme?",
                "¿Hay algo más detrás de eso?",
                "Mm… siento que hay algo que no me estás diciendo.",
            ])
        return pick(CURIOSITY_QUESTIONS)

    # ============================================================
    # GENERACIÓN DE RESPUESTAS v0.9.0
    # ============================================================

    def _generate_response(
        self,
        action: str,
        emotion: EmotionalState,
        special_content: Optional[str],
        important_facts: dict,
        context: Dict[str, Any],
        traits: dict,
        empathy_bonus: float,
        relationship_score: float,
        name: str = "tú",
        is_humor: bool = False,
        user_id: str = None,
    ) -> str:

        trust_lvl = trust_level(emotion.trust)
        energy    = emotion.energy
        emo       = emotion.primary_emotion.value

        if action == "ignore":
            return pick(RESPUESTAS["ignore"])

        if action == "hostile_response":
            raw = pick(RESPUESTAS["hostile_response"].get(trust_lvl, ["…"]))
            return self._inject_name(raw, name)

        if action == "reveal_secret":
            secret   = special_content or "a veces me pregunto muchas cosas"
            opciones = RESPUESTAS["reveal_secret"].get(trust_lvl, ["Mm… {secret}"])
            base     = pick(opciones).format(secret=secret)
            base     = self._inject_name(base, name)
            return self._wrap(base, energy, emotion.trust, context)

        emo_templates = RESPUESTAS["respond"].get(emo, RESPUESTAS["respond"]["neutral"])
        opciones      = emo_templates.get(trust_lvl, emo_templates.get("trust_mid", ["Mm…"]))
        base          = self._inject_name(pick(opciones), name)

        if is_humor and emotion.trust > 50:
            humor_extras = ["jeje", "😄", "ja", "qué bueno eso jeje"]
            base = base.rstrip() + f" {random.choice(humor_extras)}"

        # Humor del día (probabilidad baja, solo en estado neutral/feliz)
        if (
            user_id
            and emo in ("neutral", "happy")
            and emotion.trust > 40
            and random.random() < getattr(settings, "SOFIA_MOOD_SHARE_PROB", 0.12)
        ):
            mood_expr = sofia_mood_expression(user_id)
            base = f"{mood_expr} {base}"

        return self._wrap(base, energy, emotion.trust, context, {}, traits, empathy_bonus)

    def _wrap(
        self,
        base: str,
        energy: float,
        trust: float,
        context: Dict[str, Any],
        important_facts: dict = {},
        traits: dict = {},
        empathy_bonus: float = 0.0,
    ) -> str:
        parts = []

        micro = micro_expresion(energy, trust)
        if micro and not base.startswith(micro.strip()):
            base = base[0].lower() + base[1:] if base else base
        parts.append((micro + base).strip())

        if trust > 40:
            ctx_phrase = self._pick_context_phrase(context)
            if ctx_phrase:
                parts.append(ctx_phrase)

        if energy > 60 and trust > 60:
            extra = self._pick_extra_safe(traits, empathy_bonus)
            if extra:
                parts.append(extra)

        return " ".join(p for p in parts if p)

    def _pick_extra_safe(self, traits: dict, empathy_bonus: float) -> str:
        extras = []
        if traits.get("curiosity", 50) > 55:
            extras.append(pick(["¿Y luego qué pasó?", "Cuéntame más, ¿ok?"]))
        if traits.get("sensitivity", 50) > 65 and empathy_bonus >= 0:
            extras.append(pick(MARCA_PERSONAL))
        return pick(extras) if extras else ""

    def _pick_context_phrase(self, context: Dict[str, Any]) -> str:
        from config.sofia_voice import CONTEXTO
        if context.get("push_pull"):
            return pick(CONTEXTO["push_pull"])
        rep = context.get("repetition_level", 0)
        if rep >= 2:
            return pick(CONTEXTO["repeticion_fuerte"])
        if rep == 1:
            return pick(CONTEXTO["repeticion_leve"])
        if context.get("emotional_swing"):
            key = "swing_positivo" if context.get("swing_direction") == "positive" else "swing_negativo"
            return pick(CONTEXTO[key])
        return ""

    def _get_secret(self) -> str:
        secrets = [
            "a veces me pregunto si la gente de verdad me escucha.",
            "me gusta más el silencio que el ruido.",
            "a veces finjo que todo está bien cuando no lo está.",
            "hay cosas que no le cuento a nadie, nomás las pienso.",
            "me pregunto si los humanos también sienten cambios de energía como yo.",
        ]
        return random.choice(secrets)

    # ============================================================
    # ANÁLISIS DE CONTEXTO
    # ============================================================

    def _analyze_conversation_context(
        self,
        current_message: str,
        current_sentiment: float,
        recent_interactions: list,
        current_keywords: list
    ) -> Dict[str, Any]:

        context = {
            "repetition_level": 0,
            "emotional_swing": False,
            "push_pull": False,
            "swing_direction": None,
        }

        if not recent_interactions:
            return context

        current_clean   = current_message.strip().lower()
        identical_count = sum(
            1 for inter in recent_interactions
            if inter.message.strip().lower() == current_clean
        )

        if identical_count >= 2:
            context["repetition_level"] = 2
        elif identical_count == 1:
            context["repetition_level"] = 1
        else:
            current_kw      = set(w for w in current_keywords if len(w) > 4)
            keyword_repeats = 0
            for inter in recent_interactions:
                prev_kw = set(
                    w for w in self.analyzer.extract_keywords(inter.message)
                    if len(w) > 4
                )
                if len(current_kw & prev_kw) >= 2:
                    keyword_repeats += 1
            if keyword_repeats >= 2:
                context["repetition_level"] = 1

        sentiments = [
            inter.sentiment for inter in recent_interactions
            if inter.sentiment is not None
        ]

        if sentiments:
            if max(sentiments) - min(sentiments) > 0.8:
                context["emotional_swing"] = True
                avg_past = sum(sentiments) / len(sentiments)
                context["swing_direction"] = "positive" if current_sentiment > avg_past else "negative"

        if len(recent_interactions) >= 2:
            all_sents = sentiments + [current_sentiment]
            signs     = [1 if s > 0.15 else (-1 if s < -0.15 else 0) for s in all_sents]
            non_zero  = [s for s in signs if s != 0]
            if len(non_zero) >= 3:
                alternating = all(
                    non_zero[i] != non_zero[i + 1]
                    for i in range(len(non_zero) - 1)
                )
                if alternating:
                    context["push_pull"]       = True
                    context["emotional_swing"] = True

        if context["push_pull"]:
            context["repetition_level"] = 0

        return context