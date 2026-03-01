# discord/server_monitor.py
# ============================================================
# ServerMonitor — detector de silencio dinámico
# Aprende el ritmo real del server, no usa un timer fijo.
# ============================================================

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone


class ServerMonitor:
    """
    Trackea la actividad del canal y calcula cuándo
    el silencio es "real" según el ritmo histórico del server.
    """

    def __init__(self, maxlen: int = 1000):
        self._timestamps: deque[datetime] = deque(maxlen=maxlen)

    def record(self, ts: datetime = None):
        """Llámalo en cada on_message del canal."""
        self._timestamps.append(ts or datetime.now(timezone.utc))

    def dynamic_threshold(self) -> timedelta:
        """
        Umbral de silencio calculado desde el ritmo real.

        Lógica:
          - Sin historial suficiente → conservador (4h de día, 10h de noche)
          - Con historial → 8x el intervalo promedio entre mensajes
          - Ajuste nocturno: 2.5x más tolerante entre 00:00–08:00
          - Clamp: mínimo 20 min, máximo 6 horas
        """
        now   = datetime.now(timezone.utc)
        hour  = now.hour
        night = 2.5 if (0 <= hour < 8) else 1.0

        week_ago = now - timedelta(days=7)
        recent   = [t for t in self._timestamps if t > week_ago]

        if len(recent) < 5:
            return timedelta(seconds=30)

        sorted_ts = sorted(recent)
        intervals = [
            (sorted_ts[i] - sorted_ts[i - 1]).total_seconds()
            for i in range(1, len(sorted_ts))
        ]
        avg_gap   = sum(intervals) / len(intervals)
        threshold = max(30, min(21600, avg_gap * 8 * night)) 
        return timedelta(seconds=threshold)

    def is_silent(self, last_msg_ts: datetime) -> bool:
        """True si el silencio actual supera el umbral dinámico."""
        return datetime.now(timezone.utc) - last_msg_ts > self.dynamic_threshold()

    def active_users_estimate(self, user_timestamps: deque, window_minutes: int = 30) -> int:
        """
        Estima usuarios activos recientes.
        Requiere que bot.py pase un deque de (user_id, ts) en lugar de solo ts.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        return len({uid for uid, ts in user_timestamps if ts > cutoff})

    def debug_info(self) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "total_recorded":    len(self._timestamps),
            "threshold_minutes": round(self.dynamic_threshold().total_seconds() / 60, 1),
            "last_activity":     str(self._timestamps[-1]) if self._timestamps else None,
            "silence_now_secs":  round((now - self._timestamps[-1]).total_seconds())
                                 if self._timestamps else None,
        }