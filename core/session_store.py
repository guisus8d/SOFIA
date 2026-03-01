# core/session_store.py
# ============================================================
# SessionStore — administrador de UserSession por usuario.
# Extraído de DecisionEngine en v0.13.1
#
# Hoy: in-memory (dict simple).
# Mañana: implementar RedisSessionStore con la misma interfaz
#         y swappear sin tocar el engine.
#
# IMPORTANTE: no confundir con SessionManager (persistencia entre días).
# Este store vive mientras el proceso esté corriendo.
# ============================================================

from typing import Dict
from models.user_session import UserSession


class SessionStore:
    """
    Store in-memory de sesiones conversacionales.

    Interface mínima que cualquier implementación futura debe cumplir:
        get(user_id)  → UserSession
        save(user_id, session)
        delete(user_id)
    """

    def __init__(self):
        self._sessions: Dict[str, UserSession] = {}

    def get(self, user_id: str) -> UserSession:
        """Devuelve la sesión del usuario. Si no existe, crea una nueva."""
        if user_id not in self._sessions:
            self._sessions[user_id] = UserSession()
        return self._sessions[user_id]

    def save(self, user_id: str, session: UserSession) -> None:
        """Persiste la sesión (en memoria por ahora)."""
        self._sessions[user_id] = session

    def delete(self, user_id: str) -> None:
        """Elimina la sesión de un usuario (ej: reset manual)."""
        self._sessions.pop(user_id, None)

    def exists(self, user_id: str) -> bool:
        return user_id in self._sessions

    # ── Para debug / admin ───────────────────────────────────

    def all_users(self) -> list:
        return list(self._sessions.keys())

    def snapshot(self, user_id: str) -> dict:
        """Devuelve el estado serializado de una sesión (útil para logs)."""
        session = self.get(user_id)
        return session.to_dict()


# ── Interfaz para implementaciones futuras ───────────────────

class BaseSessionStore:
    """
    Contrato que debe cumplir cualquier store alternativo (Redis, etc).
    Implementar esta clase para swappear el store sin tocar el engine.
    """

    def get(self, user_id: str) -> UserSession:
        raise NotImplementedError

    def save(self, user_id: str, session: UserSession) -> None:
        raise NotImplementedError

    def delete(self, user_id: str) -> None:
        raise NotImplementedError