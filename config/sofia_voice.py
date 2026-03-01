# config/sofia_voice.py
# ── Shim de compatibilidad — NO editar aquí ──────────────────
# Todo el contenido fue migrado a config/voice/
# Este archivo solo re-exporta para que los imports existentes
# (decision_engine, test_auto, etc.) sigan funcionando sin cambios.
# ─────────────────────────────────────────────────────────────
from config.voice import *  # noqa: F401, F403
from config.voice import _normalize  # noqa: F401 (private, necesita export explícito)