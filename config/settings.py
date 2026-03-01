# config/settings.py
# ============================================================
# SocialBot v0.9.0
# CAMBIOS vs v0.8.2:
#   - NUEVO: Parámetros para personalidad viva (COOLDOWN_PERSONA_SHARE,
#     SOFIA_MOOD_SHARE_PROB, SOFIA_REACTION_PROB)
#   - VERSION sincronizada a 0.9.0
# ============================================================

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR  = BASE_DIR / "logs"

DATABASE_PATH = DATA_DIR / "bot_data.db"

BOT_NAME = "SocialBot"
VERSION  = "0.9.0"

INITIAL_ENERGY = 50.0
INITIAL_TRUST  = 50.0
MOOD_DECAY_PER_HOUR = 0.95

THRESHOLDS = {
    "respond":        0.2,
    "reveal_secret":  0.8,
    "ignore":        -0.1,
    "hostile_energy": 20.0
}

FACT_DECAY_PER_DAY    = 0.9
FACT_WEIGHT_THRESHOLD = 3.0
FACT_MIN_WEIGHT       = 0.5

# FIX: Reducidos para que la recuperación sea gradual y no instantánea
REPAIR_ENERGY_BOOST  = 3.0
REPAIR_TRUST_BOOST   = 2.0
APOLOGY_MULTIPLIER   = 1.2
AFFECTION_MULTIPLIER = 1.2

# Número de mensajes de disculpa necesarios para completar recuperación
RECOVERY_MESSAGES_REQUIRED = 3

EMOTIONAL_SWING_THRESHOLD  = 0.8
KEYWORD_OVERLAP_MIN_LENGTH = 4
KEYWORD_OVERLAP_MIN_COUNT  = 2

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ── Sistema de Agresión Contextual ───────────────────────────────
AGGRESSION_BOUNDARY_BOOST  = 5.0

# ── Momentum Conversacional ───────────────────────────────────────
SHORT_RESPONSE_STREAK_MAX  = 3

# ── Curiosidad Activa ─────────────────────────────────────────────
CURIOSITY_TRIGGER_PROB     = 0.30
CURIOSITY_TRUST_MIN        = 50.0

# ── Memoria Episódica (v0.8.0) ────────────────────────────────────
MAX_IMPORTANT_QUOTES       = 10    # máximo de frases memorables por usuario
QUOTE_MIN_LENGTH           = 15    # longitud mínima para guardar una frase como memorable
QUOTE_RECALL_PROB          = 0.15  # probabilidad de recordar una frase en respuesta

# ── Modo Noche (v0.8.0) ───────────────────────────────────────────
NIGHT_MODE_START_HOUR      = 22    # hora en que inicia el modo noche (22:00)
NIGHT_MODE_END_HOUR        = 6     # hora en que termina el modo noche (06:00)

# ── Backend de Sentimiento (v0.8.0) ──────────────────────────────
# Opciones: "basic" (palabras clave, sin dependencias)
#           "pysentimiento" (modelo IA, requiere: pip install pysentimiento)
SENTIMENT_BACKEND          = "basic"

# ── Secrets reset diario (v0.8.0) ────────────────────────────────
SECRETS_DAILY_RESET        = True   # Si True, secrets_revealed se resetea cada día

# ── Memoria Semántica (v0.8.2) ────────────────────────────────────
# Extrae hechos estructurados {tema: valor} de los mensajes del usuario.
SEMANTIC_FACTS_MAX         = 20     # máximo de hechos semánticos por usuario
SEMANTIC_CONFIDENCE_MIN    = 0.6    # confianza mínima para guardar un hecho
SEMANTIC_RECALL_ON_CHECK   = True   # activar recall automático en memory_check intent

# ── Intent Classifier (v0.8.2) ───────────────────────────────────
# Prioridad explícita: memory_check > identity > topic > fallback
INTENT_PRIORITY = [
    "memory_check",    # "¿recuerdas...?" / "¿te acuerdas...?" / "¿sabes algo de mí?"
    "identity",        # "¿cómo te llamas?" / "eres un bot?" etc
    "cuentame",        # "cuéntame algo" / "dime algo"
    "direct_question", # preguntas concretas con respuesta directa
    "opinion",         # temas con opinión registrada
    "topic",           # topic lock
    "fallback",        # respuesta base
]

# ── Cooldowns por tipo de output (v0.8.2) ────────────────────────
# Evita que el mismo tipo de extensión se repita demasiado seguido.
COOLDOWN_NIGHT_COMMENT     = 5      # mensajes mínimos entre comentarios nocturnos
COOLDOWN_QUOTE_RECALL      = 8      # mensajes mínimos entre quote recalls
COOLDOWN_CURIOSITY_Q       = 4      # mensajes mínimos entre preguntas de curiosidad
COOLDOWN_SEMANTIC_RECALL   = 6      # mensajes mínimos entre recalls semánticos

# ── Personalidad Viva (NUEVO v0.9.0) ─────────────────────────────
# Sofía comparte algo de sí misma en vez de solo reaccionar al usuario.
# Hace preguntas porque quiere saber, no solo por protocolo.
COOLDOWN_PERSONA_SHARE     = 5      # mensajes mínimos entre auto-shares de Sofía
SOFIA_MOOD_SHARE_PROB      = 0.12   # probabilidad de que Sofía mencione su humor al responder
SOFIA_REACTION_PROB        = 0.25   # prob. de reacción con algo propio (en vez de solo preguntar)

# ============================================================
# PARCHE PARA config/settings.py
# SocialBot v0.10.0
#
# Añade este bloque al FINAL de tu settings.py
# ============================================================

# ── Herramientas externas (v0.10.0) ──────────────────────────────
# Controla cuándo y cómo Sofía usa búsqueda web.

TOOLS_ENABLED            = True    # master switch — False desactiva todo
SEARCH_ENABLED           = True    # activa/desactiva solo búsqueda web
SEARCH_MIN_TRUST         = 0.0     # confianza mínima para buscar (0 = siempre)
SEARCH_COOLDOWN          = 3       # mensajes mínimos entre búsquedas del mismo usuario
SEARCH_MAX_SNIPPET_LEN   = 280     # chars máximos del snippet antes de cortar
DISCORD_INITIATIVE_COOLDOWN_HOURS   = 0.01
DISCORD_INITIATIVE_PROBABILITY      = 0.5   # con razón temática
DISCORD_INITIATIVE_PROBABILITY_IDLE = 0.15  # sin razón, solo silencio



