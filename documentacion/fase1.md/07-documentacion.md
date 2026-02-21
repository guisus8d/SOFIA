💓 Paso 5: Core - Emotion Engine
core/emotion_engine.py

Maneja el estado emocional y sus transiciones.
python

# core/emotion_engine.py
from typing import Optional
from models.state import EmotionalState, Emotion
from models.interaction import Interaction
from core.memory import Memory
from utils.logger import logger
import time

class EmotionEngine:
    """Gestiona el estado emocional del bot"""
    
    def __init__(self, initial_state: Optional[EmotionalState] = None):
        self.state = initial_state or EmotionalState()
        self.mood_decay = 0.95  # factor de decaimiento por hora (simulado)
        self.last_update_time = time.time()
    
    async def process_interaction(self, 
                                  interaction: Interaction, 
                                  memory: Memory) -> EmotionalState:
        """Actualiza emoción basado en nueva interacción y contexto"""
        
        # Aplicar decaimiento primero (paso del tiempo)
        self._apply_time_decay()
        
        # 1. Impacto del sentimiento del mensaje actual
        sentiment_impact = interaction.sentiment * 15  # escalado
        
        # 2. Factor histórico con este usuario
        avg_user_sentiment = memory.get_average_sentiment_for(interaction.user_id)
        history_impact = avg_user_sentiment * 10
        
        # 3. Contexto global reciente (cómo trata la comunidad)
        global_sentiment = memory.get_recent_global_sentiment()
        global_impact = global_sentiment * 5
        
        # Calcular cambio total
        total_impact = sentiment_impact + history_impact + global_impact
        
        # Actualizar energía y confianza
        self.state.energy += total_impact * 0.3
        self.state.trust += total_impact * 0.2
        
        # Limitar rangos
        self.state.energy = max(0, min(100, self.state.energy))
        self.state.trust = max(0, min(100, self.state.trust))
        
        # Determinar nueva emoción primaria
        self._update_primary_emotion()
        
        # Registrar timestamp
        self.state.last_updated = interaction.timestamp.timestamp()
        self.last_update_time = time.time()
        
        logger.info(f"Emoción actualizada: {self.state.primary_emotion.value} (energía={self.state.energy:.1f}, confianza={self.state.trust:.1f})")
        return self.state
    
    def _update_primary_emotion(self):
        """Lógica de transición de emociones"""
        e = self.state.energy
        t = self.state.trust
        
        if e < 20:
            self.state.primary_emotion = Emotion.SAD
        elif e > 80 and t > 70:
            self.state.primary_emotion = Emotion.HAPPY
        elif t < 30:
            self.state.primary_emotion = Emotion.ANGRY
        elif e < 40 and t < 40:
            self.state.primary_emotion = Emotion.FEARFUL
        else:
            self.state.primary_emotion = Emotion.NEUTRAL
    
    def _apply_time_decay(self):
        """Aplica decaimiento natural según tiempo transcurrido"""
        now = time.time()
        hours_passed = (now - self.last_update_time) / 3600  # horas
        if hours_passed <= 0:
            return
        
        # Decaimiento exponencial
        decay_factor = self.mood_decay ** hours_passed
        self.state.energy *= decay_factor
        self.state.trust *= decay_factor
        
        # Asegurar rangos
        self.state.energy = max(0, min(100, self.state.energy))
        self.state.trust = max(0, min(100, self.state.trust))
        self.last_update_time = now

