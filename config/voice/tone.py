# config/voice/tone.py
# ============================================================
# Sistema de expresión por tono (v0.10.0)
# Conecta EmotionRegistry con la voz de Sofía.
#
# Regla de oro:
#   - La LÓGICA de qué decir → decision_engine
#   - El CÓMO suena → aquí
#   - El random solo aparece en esta capa
# ============================================================

import random
import re as _re

# ── Openers por tono ────────────────────────────────────────

TONE_OPENERS = {
    "warm":          ["Oye, ",  "Ay, ",     "Jeje, ",   ""],
    "playful":       ["Jeje, ", "¡Oye! ",   "Ay jeje, ", "Mm, ", ""],
    "neutral":       ["",       "Oye, ",    "Mm, ",      "",     ""],
    "slightly_cold": ["Mm… ",   "Oye. ",    "…",         "",     ""],
    "cold":          ["…",      "Mm.",      "",          ".",    ""],
}

# ── Cierres por tono ────────────────────────────────────────

TONE_CLOSERS = {
    "warm": [
        "Estoy aquí contigo.",
        "Me alegra que me lo cuentes.",
        "Cuéntame más si quieres.",
    ],
    "playful": [
        "Jeje, ¿qué más?",
        "Oye, eso está bueno.",
        "Mm… sigue.",
    ],
    "neutral":       [],
    "slightly_cold": [],
    "cold":          [],
}


def micro_expresion_v2(energy: float, trust: float, tone: str = "neutral") -> str:
    """
    Versión tone-aware de micro_expresion.
    Retorna un opener acorde al tono interno de Sofía.
    """
    if random.random() < 0.45:
        return ""
    openers = TONE_OPENERS.get(tone, TONE_OPENERS["neutral"])
    return random.choice(openers)


def apply_verbosity(text: str, verbosity: str) -> str:
    """
    Ajusta el largo de la respuesta según el hint de verbosidad.

    verbose → sin cambios
    medium  → hasta 2 oraciones
    brief   → solo la primera oración
    """
    if verbosity == "verbose" or not text:
        return text

    sentences = _re.split(r'(?<=[.!?…])\s+', text.strip())
    sentences = [s for s in sentences if s.strip()]

    if not sentences:
        return text

    if verbosity == "brief":
        return sentences[0].strip()

    if verbosity == "medium" and len(sentences) > 2:
        return " ".join(sentences[:2]).strip()

    return text


def initiative_allows_question(initiative: str) -> bool:
    """
    True si la iniciativa permite que Sofía agregue preguntas.

    low    → no agrega preguntas espontáneas
    medium → puede agregar si la respuesta lo pide naturalmente
    high   → busca activamente hacer preguntas
    """
    return initiative != "low"


def pick_by_tone(lista: list, tone: str) -> str:
    """
    Elige una respuesta de la lista considerando el tono actual.

    cold/slightly_cold → prefiere respuestas cortas (≤ 55 chars)
    warm/playful       → prefiere respuestas con pregunta o más largas
    neutral            → elige al azar
    """
    if not lista:
        return ""

    if tone in ("cold", "slightly_cold"):
        short = [r for r in lista if len(r) <= 55]
        return random.choice(short) if short else random.choice(lista)

    if tone in ("warm", "playful"):
        rich = [r for r in lista if "?" in r or len(r) > 55]
        return random.choice(rich) if rich else random.choice(lista)

    return random.choice(lista)


def tone_closer(tone: str) -> str:
    """
    Retorna un cierre opcional según el tono.
    Solo activo en warm/playful. Vacío en cold/neutral.
    """
    closers = TONE_CLOSERS.get(tone, [])
    return random.choice(closers) if closers and random.random() < 0.25 else ""