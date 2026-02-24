# utils/aggression_detector.py
# ============================================================
# SocialBot v0.8.0
# FIX CRÍTICO: Uso de word boundaries (re.search con \b) en lugar de
#   `phrase in msg_norm` — antes "calla" matcheaba en "caballero",
#   "calle", etc. provocando falsos positivos graves.
# NUEVO: Reducción de impacto si el usuario está en modo humor.
# ============================================================

import re
import unicodedata


INSULT_LEVELS = {
    "leve": [
        "wey", "guey", "tonto", "tonta", "idiota", "imbecil",
        "mensa", "menso", "tarado", "tarada", "baboso", "babosa",
        "naco", "naca", "pesado", "pesada", "estupido", "estupida",
        "callate", "calla",
    ],
    "medio": [
        "eres una basura", "eres una mierda", "te odio",
        "no sirves", "eres inutil", "que asco",
        "eres horrible", "eres un fracaso", "me haces perder el tiempo",
        "eres lo peor", "a nadie le importas", "eres patetica",
        "eres patetico", "maldito bot", "eres una porqueria",
    ],
    "alto": [
        "vete al diablo", "vete a la chingada", "a la verga",
        "chinga tu madre", "ojete", "te voy a bloquear",
        "eres una maldita", "eres un maldito", "ojala te mueras",
        "cierra la boca", "callate la boca",
    ],
}

IMPACT_WEIGHTS = {
    "leve":  {"energy": -8.0,  "trust": -6.0,  "damage": 1.0},
    "medio": {"energy": -15.0, "trust": -12.0, "damage": 2.5},
    "alto":  {"energy": -25.0, "trust": -18.0, "damage": 4.0},
}

JOKE_INDICATORS = {"jaja", "jeje", "jajaja", "jejeje", "lol", "xd", ":v", "😂", "🤣"}


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFD", text)
    return nfkd.encode("ascii", "ignore").decode("utf-8").lower()


def _match_phrase(phrase: str, text_norm: str) -> bool:
    """
    FIX CRÍTICO: Usa word boundaries para palabras simples.
    Para frases multi-palabra usa búsqueda de subcadena (más natural).
    Antes: `phrase in text_norm` → "calla" matcheaba en "caballero".
    """
    if " " in phrase:
        # Frase multi-palabra: subcadena es suficiente
        return phrase in text_norm
    else:
        # Palabra simple: respetar boundaries
        pattern = r'\b' + re.escape(phrase) + r'\b'
        return bool(re.search(pattern, text_norm))


class AggressionDetector:
    """
    Detecta insultos con 3 niveles (leve / medio / alto).
    Si parece broma Y trust > 75, reduce el impacto a 40%.
    """

    def detect(self, message: str, trust: float = 50.0) -> dict:
        """
        Retorna:
          {
            "detected":  bool,
            "level":     str | None,
            "impact":    dict | None,
            "is_joke":   bool,
          }
        """
        msg_norm  = _normalize(message)
        msg_lower = message.lower()
        is_joke   = any(ind in msg_lower for ind in JOKE_INDICATORS)

        for level in ("alto", "medio", "leve"):
            for phrase in INSULT_LEVELS[level]:
                if _match_phrase(phrase, msg_norm):        # ← FIX aplicado
                    impact = IMPACT_WEIGHTS[level].copy()
                    reported_level = level

                    # Broma entre amigos → impacto reducido
                    if is_joke and trust > 75:
                        impact = {k: v * 0.4 for k, v in impact.items()}
                        reported_level = "leve"

                    return {
                        "detected": True,
                        "level":    reported_level,
                        "impact":   impact,
                        "is_joke":  is_joke,
                    }

        return {"detected": False, "level": None, "impact": None, "is_joke": False}