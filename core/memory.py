# core/memory.py

from typing import Dict, List, Optional
from datetime import datetime
from models.interaction import Interaction
from storage.database import Database
from utils.logger import logger


class Memory:
    """Sistema de memoria del bot
    - Corto plazo (RAM)
    - Largo plazo (Base de datos)
    """

    def __init__(self, db: Database):
        self.db = db
        self.short_term: List[Interaction] = []  # últimas 10 interacciones globales
        self.user_last_interaction: Dict[str, datetime] = {}  # cache rápido por usuario

    # ------------------------------------------------------------
    # ALMACENAMIENTO
    # ------------------------------------------------------------

    async def remember(self, interaction: Interaction):
        """Guarda una interacción en memoria (corto y largo plazo)"""

        # 🔹 Memoria a corto plazo (RAM)
        self.short_term.append(interaction)
        if len(self.short_term) > 10:
            self.short_term.pop(0)

        # 🔹 Actualizar última interacción del usuario
        self.user_last_interaction[interaction.user_id] = interaction.timestamp

        # 🔹 Memoria a largo plazo (BD)
        try:
            self.db.save_interaction(interaction)
            logger.debug(f"Interacción guardada para usuario {interaction.user_id}")
        except Exception as e:
            logger.error(f"Error guardando interacción: {e}")

    # ------------------------------------------------------------
    # RECALL
    # ------------------------------------------------------------

    async def recall_user(self, user_id: str, limit: int = 5) -> List[Interaction]:
        """Recupera interacciones recientes de un usuario desde BD"""
        try:
            return self.db.get_user_interactions(user_id, limit)
        except Exception as e:
            logger.error(f"Error recuperando interacciones: {e}")
            return []

    async def get_recent_interactions(self, user_id: str, limit: int = 3) -> List[Interaction]:
        """Retorna las últimas 'limit' interacciones con el usuario (ventana contextual v0.3.5)"""
        return await self.recall_user(user_id, limit)

    def get_last_interaction_with(self, user_id: str) -> Optional[Interaction]:
        """Busca en memoria corta la última interacción con el usuario"""
        for interaction in reversed(self.short_term):
            if interaction.user_id == user_id:
                return interaction
        return None

    # ------------------------------------------------------------
    # MÉTRICAS EMOCIONALES
    # ------------------------------------------------------------

    def get_average_sentiment_for(self, user_id: str) -> float:
        """Sentimiento promedio histórico del usuario"""
        try:
            return self.db.get_average_sentiment_for_user(user_id)
        except Exception as e:
            logger.error(f"Error calculando sentimiento promedio: {e}")
            return 0.0

    def get_recent_global_sentiment(self) -> float:
        """Sentimiento promedio de las últimas interacciones globales (RAM)"""
        if not self.short_term:
            return 0.0

        sentiments = [
            i.sentiment for i in self.short_term
            if i.sentiment is not None
        ]

        if not sentiments:
            return 0.0

        return sum(sentiments) / len(sentiments)