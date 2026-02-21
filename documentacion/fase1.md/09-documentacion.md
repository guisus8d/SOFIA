⚙️ Paso 7: Configuración
config/settings.py

Variables de configuración centralizadas.
python

# config/settings.py
import os
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

# Base de datos
DATABASE_PATH = DATA_DIR / "bot_data.db"

# Bot
BOT_NAME = "SocialBot"
VERSION = "0.1.0"

# Emociones
INITIAL_ENERGY = 50.0
INITIAL_TRUST = 50.0
MOOD_DECAY_PER_HOUR = 0.95

# Umbrales (ajustables)
THRESHOLDS = {
    "respond": 0.2,
    "reveal_secret": 0.8,
    "ignore": -0.1,
    "hostile_energy": 20.0  # por debajo de 20 de energía, hostil
}

# Crear directorios necesarios
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)