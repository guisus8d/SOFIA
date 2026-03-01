# discord/initiative_trigger.py
# ============================================================
# InitiativeTrigger — decide si Sofía habla por iniciativa propia
# Todas las reglas de supresión viven aquí, no en bot.py
# ============================================================

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Optional, TYPE_CHECKING

from config import settings

if TYPE_CHECKING:
    from discord.server_monitor import ServerMonitor
    from discord.channel_memory import ChannelMemory


class InitiativeTrigger:
    """
    Única responsabilidad: responder True/False a "¿debe Sofía hablar ahora?".
    No construye el mensaje, no accede a Discord, solo evalúa reglas.
    """

    def should_speak(
        self,
        monitor:            "ServerMonitor",
        channel_memory:     "ChannelMemory",
        last_msg_ts:        datetime,
        last_initiative_ts: Optional[datetime],
    ) -> bool:

        # ── Regla 0: mensaje emocionalmente pesado reciente ──
        # Confesión, crisis, ideación. Sofía no interrumpe eso.
        heavy_cooldown = getattr(settings, "DISCORD_HEAVY_COOLDOWN_HOURS", 4)
        if channel_memory.heavy_is_recent(cooldown_hours=heavy_cooldown):
            return False

        # ── Regla 1: cooldown duro entre iniciativas ─────────
        # Sin esto Sofía puede volverse pesada si el server está dormido.
        cooldown_h = getattr(settings, "DISCORD_INITIATIVE_COOLDOWN_HOURS", 3)
        if last_initiative_ts:
            if datetime.now(timezone.utc) - last_initiative_ts < timedelta(hours=cooldown_h):
                return False

        # ── Regla 2: el silencio no es suficientemente largo ─
        if not monitor.is_silent(last_msg_ts):
            return False

        # ── Regla 3: conflicto muy reciente → esperar más ────
        # Si hubo pelea hace menos de 30 min, no entrar todavía.
        # post_conflict SÍ es válido, pero solo pasados 30 min.
        if channel_memory.conflict_is_recent(cooldown_hours=0.5):
            return False

        # ── Regla 4: ¿hay razón contextual? ──────────────────
        reason = channel_memory.get_initiative_reason()

        if reason is None:
            # Sin tema ni evento — probabilidad muy baja
            prob = getattr(settings, "DISCORD_INITIATIVE_PROBABILITY_IDLE", 0.15)
            return random.random() < prob

        # ── Regla 5: probabilidad ponderada por fuerza ───────
        # Un burst fuerte (strength=0.9) tiene ~45% de chance.
        # Un tema débil (strength=0.3) tiene ~15% de chance.
        base_prob = getattr(settings, "DISCORD_INITIATIVE_PROBABILITY", 0.5)
        adjusted  = base_prob * reason.strength
        return random.random() < adjusted