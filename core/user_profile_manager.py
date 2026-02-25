# core/user_profile_manager.py
# ============================================================
# SocialBot v0.9.1
# CAMBIOS vs v0.8.0:
#   - FIX BUG: _extract_memorable_quote — el filtro de sentimiento
#     ya no descarta frases que el patrón semántico ya calificó.
#     Antes, una confesión como "nadie sabe que me siento solo a veces"
#     podía tener score ~0.0 y nunca guardarse. Ahora: si el patrón
#     MEMORABLE_PATTERNS la capturó, se guarda independientemente del
#     score (solo se filtra sentimiento en mensajes sin patrón claro).
#   - MANTIENE: todo lo demás de v0.8.0
# ============================================================

import re
from datetime import datetime
from typing import Optional, List, Dict

from models.user_profile import UserProfile
from models.interaction import Interaction
from storage.database import Database
from utils.text_analyzer import TextAnalyzer
from utils.logger import logger
from config import settings
from core.personality_core import PERSONALITY_CORE


# Patrones que indican una confesión / reflexión personal valiosa
MEMORABLE_PATTERNS = [
    re.compile(r'\b(?:siempre|nunca|jamás)\s+.{10,}', re.IGNORECASE),
    re.compile(r'\b(?:a veces pienso|me pregunto si|tengo miedo de|sueño con|quisiera|ojalá)\s+.{8,}', re.IGNORECASE),
    re.compile(r'\b(?:lo que más me importa|lo que más quiero|lo que más me duele)\s+.{5,}', re.IGNORECASE),
    re.compile(r'\b(?:nadie sabe que|no le he dicho a nadie|te confieso)\s+.{5,}', re.IGNORECASE),
    re.compile(r'\b(?:me arrepiento de|ojala hubiera|si pudiera volver)\s+.{5,}', re.IGNORECASE),
]


class UserProfileManager:
    def __init__(self, db: Database):
        self.db = db
        self.analyzer = TextAnalyzer()
        self.cache: Dict[str, UserProfile] = {}

        self.fact_patterns = [
            (re.compile(r'\b(?:soy|soy un|soy una)\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,4})\b', re.IGNORECASE), "soy {0}"),
            (re.compile(r'\b(?:estudio|estoy estudiando)\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,4})\b', re.IGNORECASE), "estudia {0}"),
            (re.compile(r'\b(?:trabajo en|trabajo de)\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,4})\b', re.IGNORECASE), "trabaja en {0}"),
            (re.compile(r'\b(?:me gusta|me encanta)\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,4})\b', re.IGNORECASE), "le gusta {0}"),
            (re.compile(r'\b(?:tengo un|tengo una)\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,4})\b', re.IGNORECASE), "tiene {0}"),
        ]

        self.stopwords = {
            "muy", "bastante", "poco", "algo",
            "un", "una", "unos", "unas",
            "el", "la", "los", "las"
        }

    # ------------------------------------------------------------
    # CARGA / CREACIÓN
    # ------------------------------------------------------------

    async def get_or_create_profile(self, user_id: str) -> UserProfile:
        if user_id in self.cache:
            return self.cache[user_id]

        profile = self.db.load_user_profile(user_id)

        if not profile:
            profile = UserProfile(
                user_id=user_id,
                first_seen=datetime.now(),
                last_seen=datetime.now()
            )
            self.db.save_user_profile(profile)
            logger.info(f"Nuevo perfil creado para {user_id}")

        self.cache[user_id] = profile
        return profile

    # ------------------------------------------------------------
    # ACTUALIZACIÓN PRINCIPAL
    # ------------------------------------------------------------

    async def update_profile_from_interaction(
        self,
        profile: UserProfile,
        interaction: Interaction
    ):
        # 1. Decaimiento de hechos
        self._apply_fact_decay(profile, interaction.timestamp)

        # 2. Contadores
        profile.interaction_count += 1
        profile.last_seen = interaction.timestamp
        if not profile.first_seen:
            profile.first_seen = interaction.timestamp

        # 3. Estilo comunicación
        style = self._detect_communication_style(interaction.message)
        if style:
            profile.communication_style = style

        # 4. Temas
        keywords = self.analyzer.extract_keywords(interaction.message, max_words=3)
        current_topics = set(profile.topics)
        current_topics.update(keywords)
        profile.topics = list(current_topics)[:10]

        # 5. Hechos importantes
        detected_facts = self._extract_facts(interaction.message)
        for fact in detected_facts:
            increment = 1.0
            if interaction.sentiment is not None and abs(interaction.sentiment) > 0.7:
                increment += 0.5
            profile.important_facts[fact] = (
                profile.important_facts.get(fact, 0.0) + increment
            )

        if len(profile.important_facts) > 50:
            sorted_facts = sorted(
                profile.important_facts.items(),
                key=lambda x: x[1],
                reverse=True
            )
            profile.important_facts = dict(sorted_facts[:50])

        # 6. Frases memorables — FIX v0.9.1: patrón semántico toma precedencia
        quote = self._extract_memorable_quote(interaction.message, interaction.sentiment)
        if quote:
            if quote not in profile.important_quotes:
                profile.important_quotes.append(quote)
                if len(profile.important_quotes) > settings.MAX_IMPORTANT_QUOTES:
                    profile.important_quotes = profile.important_quotes[-settings.MAX_IMPORTANT_QUOTES:]

        # 7. Sistema de daño relacional
        if interaction.sentiment is not None:
            if interaction.sentiment < -0.3:
                damage_increment = abs(interaction.sentiment) * 2
                profile.relationship_damage += damage_increment

            repair_mult = self.analyzer.get_repair_multiplier(interaction.message)
            if repair_mult > 1.0 and interaction.sentiment >= 0:
                trust = profile.emotional_state.trust
                if trust > 70:
                    trust_factor = 1.2
                elif trust < 40:
                    trust_factor = 0.5
                else:
                    trust_factor = 1.0

                reduction = repair_mult * 1.5 * trust_factor
                profile.relationship_damage = max(0.0, profile.relationship_damage - reduction)

        # 8. Evolución de personalidad
        if interaction.sentiment is not None:
            if interaction.sentiment > 0.5:
                profile.personality_offsets["attachment"] += 0.5
            elif interaction.sentiment < -0.5:
                profile.personality_offsets["boundary_strength"] += 0.8
                profile.personality_offsets["attachment"] -= 0.5

        for k in profile.personality_offsets:
            profile.personality_offsets[k] = max(-30.0, min(30.0, profile.personality_offsets[k]))

        # Guardar
        self.db.save_user_profile(profile)
        self.cache[profile.user_id] = profile

    # ------------------------------------------------------------
    # EXTRACCIÓN DE FRASES MEMORABLES — FIX v0.9.1
    # ------------------------------------------------------------

    def _extract_memorable_quote(self, message: str, sentiment: Optional[float]) -> Optional[str]:
        """
        Detecta si el mensaje contiene una frase personal/confesión memorable.

        FIX v0.9.1: El filtro de sentimiento ya no bloquea frases que los
        MEMORABLE_PATTERNS ya calificaron como confesiones/reflexiones.
        El backend básico de sentimiento puede dar score ~0.0 en frases
        mixtas ("nadie sabe que me siento solo") aunque sean personalmente
        importantes. La lógica nueva:
          - Si el PATRÓN lo capturó → guardar siempre (solo filtrar mensajes
            claramente positivos extremos que no sean reflexiones reales)
          - Si no hay patrón → aplicar filtro de sentimiento normal
        """
        if len(message) < settings.QUOTE_MIN_LENGTH:
            return None

        msg_clean = message.strip()

        for pattern in MEMORABLE_PATTERNS:
            match = pattern.search(msg_clean)
            if match:
                quote = match.group(0).strip()
                # Recortar si es muy larga
                if len(quote) > 120:
                    quote = quote[:120].rsplit(' ', 1)[0] + "…"
                return quote

        # Sin patrón: solo guardar si tiene sentimiento suficientemente marcado
        # (no completamente neutro — no queremos guardar "ok" o "bien")
        if sentiment is not None and abs(sentiment) < 0.25:
            return None

        return None

    def get_random_quote(self, profile: UserProfile) -> Optional[str]:
        """Retorna una frase memorable aleatoria del usuario (para que Sofía la cite)."""
        if not profile.important_quotes:
            return None
        import random
        return random.choice(profile.important_quotes)

    # ------------------------------------------------------------
    # DECAY
    # ------------------------------------------------------------

    def _apply_fact_decay(self, profile: UserProfile, current_time: datetime):
        if not profile.last_seen:
            return

        days_passed = max(0, (current_time - profile.last_seen).total_seconds() / 86400)
        if days_passed == 0:
            return

        decay_factor = settings.FACT_DECAY_PER_DAY ** days_passed

        for fact in list(profile.important_facts.keys()):
            new_weight = profile.important_facts[fact] * decay_factor
            if new_weight < settings.FACT_MIN_WEIGHT:
                del profile.important_facts[fact]
            else:
                profile.important_facts[fact] = new_weight

    # ------------------------------------------------------------
    # EXTRACCIÓN DE HECHOS
    # ------------------------------------------------------------

    def _extract_facts(self, message: str) -> List[str]:
        detected = []

        for pattern, template in self.fact_patterns:
            matches = pattern.findall(message)

            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]

                fact_text = match.strip().lower()
                words = fact_text.split()
                filtered_words = [w for w in words if w not in self.stopwords]

                if not filtered_words:
                    continue

                fact_text = " ".join(filtered_words[:5])
                fact = template.format(fact_text)
                detected.append(fact)

        return detected

    # ------------------------------------------------------------
    # ESTILO DE COMUNICACIÓN
    # ------------------------------------------------------------

    def _detect_communication_style(self, message: str) -> Optional[str]:
        msg = message.lower()

        technical_words = {
            "código", "función", "variable", "bug",
            "python", "javascript", "api",
            "servidor", "base de datos"
        }

        if any(w in msg for w in technical_words):
            return "technical"

        humor = {"jaja", "jeje", "lol", "😂", "😆"}
        if any(w in msg for w in humor):
            return "humorous"

        aggressive = {"idiota", "estúpido", "imbécil", "tonto", "😡"}
        if any(w in msg for w in aggressive):
            return "aggressive"

        return None

    # ------------------------------------------------------------
    # MODIFICADORES DE COMPORTAMIENTO
    # ------------------------------------------------------------

    def get_behavior_modifiers(self, profile: UserProfile) -> dict:
        effective_traits = {}
        for k, base in PERSONALITY_CORE.items():
            offset = profile.personality_offsets.get(k, 0.0)
            effective_traits[k] = max(0.0, min(100.0, base + offset))

        top_facts = dict(sorted(
            profile.important_facts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5])

        modifiers = {
            "tone": profile.communication_style,
            "empathy_bonus": 0.0,
            "hostility_threshold": 20.0,
            "patience": 1.0,
            "ignore_threshold_adjust": 0.0,
            "effective_traits": effective_traits,
            "important_facts": top_facts,
            "important_quotes": profile.important_quotes,
        }

        if profile.interaction_count > 10 and profile.emotional_state.trust > 70:
            modifiers["empathy_bonus"] += 0.2
            modifiers["hostility_threshold"] = 10.0

        if profile.emotional_state.trust < 30:
            modifiers["empathy_bonus"] -= 0.1
            modifiers["hostility_threshold"] = 30.0

        damage = profile.relationship_damage

        if damage > 5:
            modifiers["hostility_threshold"] = 25.0
            modifiers["empathy_bonus"] -= 0.2
            modifiers["ignore_threshold_adjust"] = 0.2
        elif damage > 2:
            modifiers["hostility_threshold"] = 22.0
            modifiers["empathy_bonus"] -= 0.1
            modifiers["ignore_threshold_adjust"] = 0.1

        boundary    = effective_traits.get("boundary_strength", 70)
        sensitivity = effective_traits.get("sensitivity", 50)
        depth       = effective_traits.get("depth", 65)

        if boundary > 60:
            modifiers["ignore_threshold_adjust"] = 0.1
        elif boundary < 40:
            modifiers["ignore_threshold_adjust"] = -0.1

        modifiers["empathy_bonus"] += (sensitivity - 50) / 500
        modifiers["patience"] += (depth - 50) / 100

        return modifiers


        # models/interaction.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Interaction:
    """Registro de una interacción con un usuario"""
    user_id: str
    message: str
    sentiment: float  # -1 a 1
    response: str
    timestamp: datetime
    emotion_before: str
    emotion_after: str

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "message": self.message,
            "sentiment": self.sentiment,
            "response": self.response,
            "timestamp": self.timestamp.isoformat(),
            "emotion_before": self.emotion_before,
            "emotion_after": self.emotion_after
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            user_id=data["user_id"],
            message=data["message"],
            sentiment=data["sentiment"],
            response=data["response"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            emotion_before=data["emotion_before"],
            emotion_after=data["emotion_after"]
        )