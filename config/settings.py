# config/settings.py
# ============================================================
# SocialBot v0.6.2
# FIX: Boosts de reparación reducidos para que la confianza
#      no suba de golpe con una sola disculpa.
# ============================================================

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR  = BASE_DIR / "logs"

DATABASE_PATH = DATA_DIR / "bot_data.db"

BOT_NAME = "SocialBot"
VERSION  = "0.5.4"

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
# Antes: REPAIR_ENERGY_BOOST=6.0, REPAIR_TRUST_BOOST=4.0, APOLOGY_MULTIPLIER=1.5
REPAIR_ENERGY_BOOST  = 3.0    # ← era 6.0
REPAIR_TRUST_BOOST   = 2.0    # ← era 4.0
APOLOGY_MULTIPLIER   = 1.2    # ← era 1.5
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