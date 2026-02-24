# core/decision_engine.py
# ============================================================
# SocialBot v0.7.0
# NUEVO: Topic Lock + Priority Resolver + Control de densidad verbal
#
# Cambios respecto a v0.6.0:
#   - TopicLock: detecta y mantiene el tema activo del usuario
#     con confidence decay para cambios naturales de tema.
#   - PriorityResolver: orden fijo y estricto de decisiones.
#     No hay competencia entre módulos.
#   - Una sola pregunta por respuesta (sin efecto "terapeuta").
#   - Bug fix: discord_bot.py ya NO está anidado en esta clase.
# ============================================================

from datetime import datetime
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
    get_opinion,
    OPINIONES,
)
import random
import time


# ============================================================
# TOPIC LOCK — Sistema de bloqueo de tema activo
# ============================================================

class TopicLock:
    """
    Mantiene el tema activo por usuario.
    - confidence sube si el mensaje se parece al topic actual.
    - confidence baja si el mensaje cambia de tema.
    - Si confidence < MIN_CONFIDENCE → se libera el topic.
    """

    MIN_CONFIDENCE = 0.3
    BOOST          = 0.15   # tema continúa
    DECAY          = 0.08   # tema cambia
    MAX_TURNS      = 12     # máximo de turnos antes de liberar

    # Mapeo de palabras clave → nombre de tema
    TOPIC_KEYWORDS: Dict[str, list] = {
        # Arte y creatividad
        "dibujo":        ["dibujo", "dibujar", "ilustracion", "boceto", "lapiz", "pincel"],
        "pintura":       ["pintura", "pintar", "acuarela", "oleo", "lienzo"],
        "musica":        ["musica", "cancion", "cantar", "instrumento", "guitarra", "piano", "banda", "letra"],
        "escritura":     ["escribir", "cuento", "historia", "poema", "novela", "texto", "escritura"],
        "fotografia":    ["foto", "fotografia", "camara", "imagen", "retrato"],
        # Tecnología
        "programacion":  ["codigo", "programa", "programar", "bug", "funcion", "python", "javascript", "api", "variable", "app"],
        "videojuegos":   ["juego", "jugar", "minecraft", "fortnite", "roblox", "valorant", "gta", "zelda", "pokemon", "partida", "nivel"],
        # Entretenimiento
        "anime":         ["anime", "manga", "otaku", "personaje", "saga", "temporada", "capitulo"],
        "peliculas":     ["pelicula", "serie", "netflix", "ver", "cine", "actor", "directora"],
        "libros":        ["libro", "leer", "novela", "autor", "lectura", "pagina"],
        # Deportes
        "futbol":        ["futbol", "gol", "partido", "equipo", "cancha", "jugador", "liga", "champions"],
        "deportes":      ["deporte", "entrenar", "gimnasio", "correr", "natacion", "basquetbol"],
        # Vida personal
        "escuela":       ["escuela", "clase", "maestro", "tarea", "examen", "universidad", "carrera", "estudiar"],
        "trabajo":       ["trabajo", "jefe", "oficina", "sueldo", "proyecto", "cliente", "empresa"],
        "familia":       ["familia", "mama", "papa", "hermano", "hermana", "abuelo", "abuela"],
        "amigos":        ["amigo", "amiga", "fiesta", "salir", "banda", "cuate"],
        # Comida
        "comida":        ["comer", "comida", "tacos", "pizza", "sushi", "hamburguesa", "ramen", "cocinar", "receta"],
        # Emociones / estado
        "salud_mental":  ["ansioso", "deprimido", "triste", "estresado", "angustia", "ansiedad", "terapia"],
        "relaciones":    ["novio", "novia", "pareja", "amor", "relacion", "ruptura", "cita", "besar"],
    }

    def __init__(self):
        # { user_id: {"name": str, "confidence": float, "turns": int, "last_updated": float} }
        self._locks: Dict[str, dict] = {}

    def _normalize(self, text: str) -> str:
        import unicodedata
        nfkd = unicodedata.normalize("NFD", text)
        return nfkd.encode("ascii", "ignore").decode("utf-8").lower()

    def detect_topic(self, message: str) -> Optional[str]:
        """Detecta el tema dominante del mensaje (o None)."""
        msg = self._normalize(message)
        # Cuenta cuántas palabras clave de cada tema aparecen
        scores: Dict[str, int] = {}
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in msg)
            if count > 0:
                scores[topic] = count
        if not scores:
            return None
        return max(scores, key=scores.get)

    def update(self, user_id: str, message: str) -> Optional[str]:
        """
        Actualiza el topic lock del usuario y retorna el topic activo (o None).
        """
        detected = self.detect_topic(message)
        lock = self._locks.get(user_id)

        if lock is None:
            # Sin topic previo
            if detected:
                self._locks[user_id] = {
                    "name": detected,
                    "confidence": 0.6,
                    "turns": 1,
                    "last_updated": time.time()
                }
                return detected
            return None

        # Hay topic previo
        if detected == lock["name"] or detected is None:
            # Mismo tema (o mensaje ambiguo) → boost
            if detected == lock["name"]:
                lock["confidence"] = min(1.0, lock["confidence"] + self.BOOST)
            else:
                # Mensaje ambiguo → pequeño decay
                lock["confidence"] = max(0.0, lock["confidence"] - self.DECAY * 0.5)
        else:
            # Tema diferente → decay
            lock["confidence"] = max(0.0, lock["confidence"] - self.DECAY)

        lock["turns"] += 1
        lock["last_updated"] = time.time()

        # Liberar si confianza muy baja o demasiados turnos sin variación
        if lock["confidence"] < self.MIN_CONFIDENCE or lock["turns"] > self.MAX_TURNS:
            del self._locks[user_id]
            # Si detectamos un nuevo tema, iniciarlo
            if detected:
                self._locks[user_id] = {
                    "name": detected,
                    "confidence": 0.6,
                    "turns": 1,
                    "last_updated": time.time()
                }
                return detected
            return None

        return lock["name"]

    def get_active(self, user_id: str) -> Optional[str]:
        lock = self._locks.get(user_id)
        return lock["name"] if lock else None

    def release(self, user_id: str):
        self._locks.pop(user_id, None)

    def get_topic_question(self, topic: str, previous_responses: list = None) -> Optional[str]:
        """
        Retorna una pregunta relacionada con el topic activo.
        Asegura variedad para no repetir plantillas.
        """
        TOPIC_QUESTIONS: Dict[str, list] = {
            "dibujo":       ["¿Qué te gusta dibujar más?", "¿Los personajes los inventas tú?", "¿Cuánto tiempo llevas dibujando?", "¿Usas referencia o de memoria?", "¿Tienes un estilo favorito?"],
            "pintura":      ["¿Qué técnica usas más?", "¿Mezclas colores a mano o digital?", "¿Tienes algún cuadro favorito propio?"],
            "musica":       ["¿Tocas algo o solo escuchas?", "¿Qué género escuchas más?", "¿Tienes artista favorito?", "¿Compones algo propio?"],
            "escritura":    ["¿Qué tipo de historias escribes?", "¿Tienes un personaje favorito de los tuyos?", "¿Escribes a mano o en computadora?"],
            "fotografia":   ["¿Qué te gusta retratar más?", "¿Editas tus fotos?", "¿Usas cámara o celular?"],
            "programacion": ["¿Qué estás construyendo?", "¿Qué lenguaje usas?", "¿Es proyecto personal o de trabajo?"],
            "videojuegos":  ["¿Qué género te gusta más?", "¿Juegas solo o con alguien?", "¿Tienes un juego favorito de toda la vida?", "¿Cuánto tiempo le dedicas?"],
            "anime":        ["¿Tienes un favorito?", "¿Lo ves en español o japonés?", "¿Hay alguno que recomiendas?"],
            "peliculas":    ["¿Qué género prefieres?", "¿Ves más series o películas?", "¿Tienes alguna favorita?"],
            "libros":       ["¿Lees seguido?", "¿Qué género te gusta?", "¿Tienes un libro favorito?"],
            "futbol":       ["¿Tienes equipo?", "¿Juegas o solo ves?", "¿Sigues alguna liga?"],
            "deportes":     ["¿Practicas alguno?", "¿Prefieres verlos o jugarlos?", "¿Cuánto tiempo le dedicas?"],
            "escuela":      ["¿Qué estudias?", "¿Cómo te va?", "¿Tienes materia favorita?"],
            "trabajo":      ["¿En qué trabajas?", "¿Te gusta lo que haces?", "¿Llevas mucho tiempo ahí?"],
            "familia":      ["¿Con quién vives?", "¿Te llevas bien con tu familia?"],
            "amigos":       ["¿Sales seguido?", "¿Tienes un mejor amigo?"],
            "comida":       ["¿Cocinas tú?", "¿Tienes platillo favorito?", "¿Qué no soportas comer?"],
            "salud_mental": ["¿Cómo has estado?", "¿Hay algo que te esté pesando?"],
            "relaciones":   ["¿Cómo van las cosas?", "¿Lo hablaste con alguien?"],
        }
        questions = TOPIC_QUESTIONS.get(topic, [])
        if not questions:
            return None
        # Evitar repetir si tenemos historial
        if previous_responses:
            unused = [q for q in questions if q not in previous_responses]
            if unused:
                return random.choice(unused)
        return random.choice(questions)


# ============================================================
# DECISION ENGINE v0.7.0
# ============================================================

class DecisionEngine:
    """Motor central de decisiones de SOFIA (v0.7.0)"""

    def __init__(self):
        self.analyzer            = TextAnalyzer()
        self.aggression_detector = AggressionDetector()
        self.topic_lock          = TopicLock()   # ← NUEVO

        self.thresholds = {
            "ignore":         -0.2,
            "reveal_secret":  95,
            "hostile_energy": 30
        }

        self.secrets_revealed: Dict[str, int]  = {}
        self.aggression_count: Dict[str, int]  = {}
        self.recovery_needed:  Dict[str, int]  = {}
        self.short_streak:     Dict[str, int]  = {}
        # Historial de preguntas de topic por usuario (evita repetición)
        self._topic_question_history: Dict[str, list] = {}

    # ============================================================
    # MÉTODO PRINCIPAL — Priority Resolver estricto
    # ============================================================

    async def decide_response(
        self,
        user_id: str,
        message: str,
        emotion: EmotionalState,
        memory: Memory,
        profile_modifiers: Optional[dict] = None,
        display_name: str = "tú",
    ) -> Dict[str, Any]:

        if profile_modifiers is None:
            profile_modifiers = {}

        name      = display_name
        sentiment = self.analyzer.analyze_sentiment(message)
        keywords  = self.analyzer.extract_keywords(message)

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
        patience          = profile_modifiers.get("patience", 1.0)
        ignore_adjust     = profile_modifiers.get("ignore_threshold_adjust", 0.0)
        ignore_threshold  = self.thresholds["ignore"] * patience + ignore_adjust
        hostile_threshold = profile_modifiers.get("hostility_threshold", self.thresholds["hostile_energy"])
        empathy_bonus     = profile_modifiers.get("empathy_bonus", 0.0)

        agg_count  = self.aggression_count.get(user_id, 0)
        rec_needed = self.recovery_needed.get(user_id, 0)
        streak     = self.short_streak.get(user_id, 0)
        is_apology = self.analyzer.is_apology(message)

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
        # PRIORITY RESOLVER — orden fijo, sin saltos
        # ════════════════════════════════════════════════════

        # PRIORIDAD 1 — Identidad
        identity_response = detect_identity_question(message)
        if identity_response:
            return self._return(user_id, message, sentiment,
                                self._inject_name(identity_response, name),
                                emotion, relationship_score, action="identity")

        # PRIORIDAD 2 — Ofensa activa
        aggression = self.aggression_detector.detect(message, trust=emotion.trust)
        if aggression["detected"]:
            if not aggression["is_joke"]:
                agg_count += 1
                self.aggression_count[user_id] = agg_count
                # Liberar topic si hay agresión seria
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

        # PRIORIDAD 3 — Recovery activo
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

        # PRIORIDAD 4 — Pregunta directa del usuario
        # (si el usuario pregunta algo explícitamente, responder con opinión)
        if agg_count == 0 and rec_needed == 0:
            opinion = get_opinion(message, name)
            if opinion:
                # Actualizar topic lock con el tema detectado
                self.topic_lock.update(user_id, message)
                return self._return(user_id, message, sentiment, opinion,
                                    emotion, relationship_score, action="opinion")

        # PRIORIDAD 5 — Topic activo
        active_topic = self.topic_lock.update(user_id, message)

        # PRIORIDAD 6 — Profundización / Acción normal
        action         = "respond"
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
        )

        # ────────────────────────────────────────────────────
        # PRIORIDAD 7 — Enriquecer con topic / curiosidad / momentum
        # ────────────────────────────────────────────────────
        # Regla: solo se agrega UNA pregunta por respuesta.
        # Si la respuesta base ya tiene "?", no agregar más.

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
            )

        return self._return(user_id, message, sentiment, response,
                            emotion, relationship_score, action=action)

    # ============================================================
    # ENRIQUECIMIENTO — una sola pregunta por respuesta
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
    ) -> str:
        """
        Agrega UNA sola pregunta/frase de enriquecimiento si la
        respuesta base no contiene ya una pregunta (?).
        Orden de prioridad:
          1. Momentum (si el usuario está muy cortito)
          2. Topic activo (si hay tema detectado)
          3. Curiosidad general (probabilística)
        """
        has_question = "?" in response

        # PRIORIDAD 7a — Momentum (respuestas muy cortas del usuario)
        if streak >= settings.SHORT_RESPONSE_STREAK_MAX:
            # El momentum ya tiene pregunta implícita → reemplazar respuesta
            return pick(MOMENTUM_DEPTH_PROMPTS)

        if has_question:
            return response  # Ya tiene pregunta, no agregar más

        # PRIORIDAD 7b — Topic activo
        if active_topic:
            history = self._topic_question_history.get(user_id, [])
            tq = self.topic_lock.get_topic_question(active_topic, history)
            if tq:
                # Guardar en historial (máx 5)
                history.append(tq)
                self._topic_question_history[user_id] = history[-5:]
                return f"{response} {tq}"

        # PRIORIDAD 7c — Curiosidad general (probabilística)
        if (
            "?" not in message
            and sentiment is not None and sentiment >= 0
            and emotion.trust >= settings.CURIOSITY_TRUST_MIN
            and traits.get("curiosity", 50) > 50
            and random.random() < settings.CURIOSITY_TRIGGER_PROB
        ):
            question = self._contextual_question(keywords, sentiment, context)
            return f"{response} {question}"

        return response

    # ============================================================
    # HELPERS
    # ============================================================

    def _inject_name(self, text: str, name: str) -> str:
        return text.replace("{name}", name)

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

    def _contextual_question(self, keywords: list, sentiment: float, context: dict) -> str:
        if sentiment > 0.5:
            return pick(["¿Cómo te sientes con eso?", "¿Eso te hizo feliz?"])
        if sentiment < -0.3:
            return pick(["¿Estás bien?", "¿Cómo te dejó eso?"])
        if context.get("repetition_level", 0) > 0:
            return pick(["¿Qué quieres realmente decirme?", "¿Hay algo más detrás de eso?"])
        return pick(CURIOSITY_QUESTIONS)

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

    # ============================================================
    # GENERACIÓN DE RESPUESTAS
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

        return self._wrap(base, energy, emotion.trust, context, important_facts, traits, empathy_bonus)

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
            extra = self._pick_extra(important_facts, traits, empathy_bonus)
            if extra:
                parts.append(extra)

        return " ".join(p for p in parts if p)

    def _pick_context_phrase(self, context: Dict[str, Any]) -> str:
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

    def _pick_extra(self, important_facts: dict, traits: dict, empathy_bonus: float) -> str:
        extras = []
        if important_facts:
            relevant = {k: v for k, v in important_facts.items() if v >= settings.FACT_WEIGHT_THRESHOLD}
            if relevant:
                top_fact = max(relevant, key=relevant.get)
                extras.append(f"Oye, recuerdo que {top_fact}. ¿Cómo va eso?")
        if traits.get("curiosity", 50) > 55:
            extras.append(pick(["¿Y luego qué pasó?", "Cuéntame más, ¿ok?"]))
        if traits.get("sensitivity", 50) > 65 and empathy_bonus >= 0:
            extras.append(pick(MARCA_PERSONAL))
        return pick(extras) if extras else ""

    def _get_secret(self) -> str:
        secrets = [
            "a veces me pregunto si la gente de verdad me escucha.",
            "me gusta más el silencio que el ruido.",
            "a veces finjo que todo está bien cuando no lo está.",
            "hay cosas que no le cuento a nadie, nomás las pienso.",
            "me pregunto si los humanos también sienten cambios de energía como yo.",
        ]
        return random.choice(secrets)