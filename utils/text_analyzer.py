# utils/text_analyzer.py
# ============================================================
# SocialBot v0.3.6 — Fix: normalización de acentos
# Cambios:
#   - Nuevo método _normalize() para quitar tildes
#   - extract_keywords y analyze_sentiment usan _normalize()
#   - Así "fútbol" y "futbol" se tratan como la misma palabra
# ============================================================

import re
import unicodedata
from typing import List
from config import settings


class TextAnalyzer:
    """Analizador de texto simple basado en palabras clave"""

    def __init__(self):
        self.positive_words = {
            "gracias", "genial", "buen", "bien", "excelente", "perfecto",
            "amor", "feliz", "alegre", "maravilloso",
            "te quiero", "te amo", "helpful", "thanks", "good", "great",
            "amo", "quiero", "adoro"
        }

        self.negative_words = {
            "mal", "peor", "odio", "estupido", "tonto", "feo",
            "horrible", "terrible", "asco",
            "imbecil", "idiota", "hate", "bad", "stupid",
            "odias", "detesto", "aborrezco"
        }

        self.intensifiers = {
            "muy", "mucho", "bastante", "demasiado",
            "super", "really", "very"
        }

        self.apology_phrases = [
            "perdon", "lo siento", "disculpa", "perdona",
            "sorry", "me equivoque", "fue mi culpa", "no quise"
        ]

        self.affection_phrases = [
            "te quiero", "te amo", "aprecio", "gracias por",
            "me importas", "eres importante", "te adoro"
        ]

    # ---------------------------
    # NORMALIZACIÓN (Fix v0.3.6)
    # ---------------------------

    def _normalize(self, text: str) -> str:
        """
        Quita tildes y convierte a minúsculas.
        'fútbol' → 'futbol', 'perdón' → 'perdon'
        """
        nfkd = unicodedata.normalize('NFD', text)
        without_accents = nfkd.encode('ascii', 'ignore').decode('utf-8')
        return without_accents.lower()

    # ---------------------------
    # SENTIMIENTO BASE
    # ---------------------------

    def analyze_sentiment(self, text: str) -> float:
        """
        Retorna un valor entre -1 (muy negativo) y 1 (muy positivo).
        Ahora normaliza acentos antes de comparar.
        """
        text_normalized = self._normalize(text)
        negation_words = {"no", "nunca", "jamas", "not", "never"}
        words = text_normalized.split()

        score = 0.0
        found_words = 0
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
    # PALABRAS CLAVE
    # ---------------------------

    def extract_keywords(self, text: str, max_words: int = 5) -> List[str]:
        """
        Extrae palabras clave normalizadas (sin tildes).
        Así 'fútbol' y 'futbol' producen la misma keyword: 'futbol'
        """
        normalized = self._normalize(text)
        words = re.findall(r'\b\w+\b', normalized)

        stopwords = {
            "de", "la", "que", "el", "en", "y", "a", "los",
            "del", "se", "las", "por", "un", "para", "con",
            "no", "una", "su", "al", "lo", "como", "mas",
            "pero", "sus", "le", "ya", "o", "fue", "este",
            "si", "mi", "hoy", "fue"
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