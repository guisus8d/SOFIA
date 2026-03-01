# utils/text_analyzer.py
# ============================================================
# SocialBot v0.8.0
# FIX 1: positive_words/negative_words separados en palabras simples
#         y positive_phrases/negative_phrases para frases multi-palabra.
#         Antes "te quiero" nunca matcheaba porque el loop era por palabra.
# FIX 2: Soporte para backend pysentimiento (modelo IA en español).
#         Configurable en settings.SENTIMENT_BACKEND.
# NUEVO:  Detección de humor general (no solo agresivo).
# ============================================================

import re
import unicodedata
from typing import List, Optional
from config import settings


class TextAnalyzer:
    """Analizador de texto con soporte para dos backends de sentimiento."""

    def __init__(self):
        # ── Palabras simples (1 token) ────────────────────────
        self.positive_words = {
            "gracias", "genial", "excelente", "perfecto",
            "feliz", "alegre", "maravilloso", "bien",
            "buen", "amo", "quiero", "adoro", "bueno",
            "helpful", "thanks", "good", "great",
        }

        self.negative_words = {
            "mal", "peor", "odio", "estupido", "tonto", "feo",
            "horrible", "terrible", "asco", "imbecil", "idiota",
            "hate", "bad", "stupid", "odias", "detesto", "aborrezco",
            # FIX v0.9.1: estados emocionales negativos del USUARIO
            # Antes "estoy triste", "me siento solo" daban sentiment=0.0
            # porque estas palabras no existían en el diccionario.
            "triste", "tristeza", "solo", "sola", "soledad",
            "llorar", "lloro", "llorando", "llore",
            "deprimido", "deprimida", "depresion",
            "angustia", "angustiado", "angustiada",
            "ansioso", "ansiosa", "ansiedad",
            "preocupado", "preocupada",
            "asustado", "asustada", "miedo",
            "cansado", "cansada", "agotado", "agotada",
            "perdido", "perdida", "vacio", "vacia",
            "desesperado", "desesperada",
        }

        # ── Frases multi-palabra (FIX: antes estaban en positive_words) ──
        self.positive_phrases = [
            "te quiero", "te amo", "muchas gracias", "me alegra",
            "me gusta", "me encanta", "que padre", "eres genial",
            "me importas", "eres importante", "te adoro",
        ]

        self.negative_phrases = [
            "no sirves", "eres un fracaso", "me cae mal",
            "no me gustas", "me haces enojar",
            # FIX v0.9.1: frases de malestar emocional del usuario
            "me siento solo", "me siento sola", "me siento triste",
            "me siento mal", "me siento perdido", "me siento perdida",
            "me siento vacio", "me siento vacia",
            "todo me sale mal", "nadie me entiende", "nadie me quiere",
            "nadie me comprende", "que mal dia", "estoy mal",
            "no tengo a nadie", "no le importo a nadie",
            "me siento solo en el mundo", "no hay nadie para mi",
        ]

        self.intensifiers = {
            "muy", "mucho", "bastante", "demasiado",
            "super", "really", "very",
        }

        self.apology_phrases = [
            "perdon", "lo siento", "disculpa", "perdona",
            "sorry", "me equivoque", "fue mi culpa", "no quise",
        ]

        self.affection_phrases = [
            "te quiero", "te amo", "aprecio", "gracias por",
            "me importas", "eres importante", "te adoro",
        ]

        # ── Humor general (NUEVO) ─────────────────────────────
        self.humor_indicators = {
            "jaja", "jeje", "lol", "xd", "jajaja", "haha",
            "😂", "🤣", "💀", ":v", "jiji",
        }

        # ── Cache para pysentimiento ──────────────────────────
        self._pysentimiento_analyzer = None
        self._backend = settings.SENTIMENT_BACKEND

        if self._backend == "pysentimiento":
            self._load_pysentimiento()

    def _load_pysentimiento(self):
        """Intenta cargar pysentimiento; si falla, cae al backend básico."""
        try:
            from pysentimiento import create_analyzer
            self._pysentimiento_analyzer = create_analyzer(
                task="sentiment", lang="es"
            )
        except ImportError:
            self._backend = "basic"

    # ---------------------------
    # NORMALIZACIÓN
    # ---------------------------

    def _normalize(self, text: str) -> str:
        """Quita tildes y convierte a minúsculas."""
        nfkd = unicodedata.normalize('NFD', text)
        without_accents = nfkd.encode('ascii', 'ignore').decode('utf-8')
        return without_accents.lower()

    # ---------------------------
    # SENTIMIENTO
    # ---------------------------

    def analyze_sentiment(self, text: str) -> float:
        """
        Retorna valor entre -1 (muy negativo) y 1 (muy positivo).
        Usa pysentimiento si está disponible, de lo contrario el método básico.
        """
        if self._backend == "pysentimiento" and self._pysentimiento_analyzer:
            return self._sentiment_pysentimiento(text)
        return self._sentiment_basic(text)

    def _sentiment_pysentimiento(self, text: str) -> float:
        """Backend IA — más preciso con sarcasmo y contexto."""
        try:
            result = self._pysentimiento_analyzer.predict(text)
            output = result.output  # "POS", "NEG", "NEU"
            probas = result.probas  # {"POS": 0.9, "NEG": 0.05, "NEU": 0.05}
            if output == "POS":
                return probas.get("POS", 0.5)
            elif output == "NEG":
                return -probas.get("NEG", 0.5)
            else:
                return 0.0
        except Exception:
            return self._sentiment_basic(text)

    def _sentiment_basic(self, text: str) -> float:
        """
        Backend básico — palabras clave.
        FIX: ahora revisa frases multi-palabra ANTES del loop por tokens.
        """
        text_normalized = self._normalize(text)
        negation_words  = {"no", "nunca", "jamas", "not", "never"}

        score       = 0.0
        found_words = 0

        # 1. Frases positivas multi-palabra
        for phrase in self.positive_phrases:
            if phrase in text_normalized:
                score += 1.0
                found_words += 1

        # 2. Frases negativas multi-palabra
        for phrase in self.negative_phrases:
            if phrase in text_normalized:
                score -= 1.0
                found_words += 1

        # 3. Palabras simples con manejo de negación e intensificadores
        words  = text_normalized.split()
        negate = False
        for i, word in enumerate(words):
            word_clean = re.sub(r'[^\w]', '', word)
            if not word_clean:
                continue

            if word_clean in negation_words:
                negate = True
                continue

            multiplier = 1.0
            if i > 0:
                prev_word = re.sub(r'[^\w]', '', words[i - 1])
                if prev_word in self.intensifiers:
                    multiplier = 1.5

            if word_clean in self.positive_words:
                score += (1.0 * multiplier) * (-1 if negate else 1)
                found_words += 1
                negate = False

            elif word_clean in self.negative_words:
                score += (-1.0 * multiplier) * (-1 if negate else 1)
                found_words += 1
                negate = False

        if found_words == 0:
            return 0.0

        return max(-1.0, min(1.0, score / found_words))

    # ---------------------------
    # HUMOR
    # ---------------------------

    def is_humor(self, text: str) -> bool:
        """Detecta si el mensaje tiene tono de humor general."""
        text_lower = text.lower()
        return any(ind in text_lower for ind in self.humor_indicators)

    # ---------------------------
    # PALABRAS CLAVE
    # ---------------------------

    def extract_keywords(self, text: str, max_words: int = 5) -> List[str]:
        """Extrae palabras clave normalizadas (sin tildes)."""
        normalized = self._normalize(text)
        words = re.findall(r'\b\w+\b', normalized)

        stopwords = {
            "de", "la", "que", "el", "en", "y", "a", "los",
            "del", "se", "las", "por", "un", "para", "con",
            "no", "una", "su", "al", "lo", "como", "mas",
            "pero", "sus", "le", "ya", "o", "fue", "este",
            "si", "mi", "hoy",
        }

        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        return keywords[:max_words]

    # ---------------------------
    # REPARACIÓN EMOCIONAL
    # ---------------------------

    def is_apology(self, text: str) -> bool:
        text_normalized = self._normalize(text)
        return any(phrase in text_normalized for phrase in self.apology_phrases)

    def is_affection(self, text: str) -> bool:
        text_normalized = self._normalize(text)
        return any(phrase in text_normalized for phrase in self.affection_phrases)

    def get_repair_multiplier(self, text: str) -> float:
        multiplier = 1.0
        if self.is_apology(text):
            multiplier *= settings.APOLOGY_MULTIPLIER
        if self.is_affection(text):
            multiplier *= settings.AFFECTION_MULTIPLIER
        return multiplier