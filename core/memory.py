# core/memory.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from models.interaction import Interaction
from storage.database import Database
from utils.logger import logger

class Memory:
    """Sistema de memoria del bot"""
    
    def __init__(self, db: Database):
        self.db = db
        self.short_term: List[Interaction] = []  # últimas 10 interacciones globales
        self.user_last_interaction: Dict[str, datetime] = {}  # caché rápido
    
    async def remember(self, interaction: Interaction):
        """Guarda una interacción en memoria (corto y largo plazo)"""
        # Memoria a corto plazo
        self.short_term.append(interaction)
        if len(self.short_term) > 10:
            self.short_term.pop(0)
        
        # Actualizar última interacción del usuario
        self.user_last_interaction[interaction.user_id] = interaction.timestamp
        
        # Memoria a largo plazo (BD)
        try:
            self.db.save_interaction(interaction)
            logger.debug(f"Interacción guardada para usuario {interaction.user_id}")
        except Exception as e:
            logger.error(f"Error guardando interacción: {e}")
    
    async def recall_user(self, user_id: str, limit: int = 5) -> List[Interaction]:
        """Recupera interacciones recientes de un usuario desde BD"""
        try:
            return self.db.get_user_interactions(user_id, limit)
        except Exception as e:
            logger.error(f"Error recuperando interacciones: {e}")
            return []
    
    def get_last_interaction_with(self, user_id: str) -> Optional[Interaction]:
        """Busca en memoria corta la última interacción con el usuario"""
        for interaction in reversed(self.short_term):
            if interaction.user_id == user_id:
                return interaction
        return None
    
    def get_average_sentiment_for(self, user_id: str) -> float:
        """Calcula sentimiento promedio desde BD (más preciso)"""
        try:
            return self.db.get_average_sentiment_for_user(user_id)
        except Exception as e:
            logger.error(f"Error calculando sentimiento promedio: {e}")
            return 0.0
    
    def get_recent_global_sentiment(self) -> float:
        """Sentimiento promedio de las últimas interacciones globales"""
        if not self.short_term:
            return 0.0
        total = sum(i.sentiment for i in self.short_term)
        return total / len(self.short_term)