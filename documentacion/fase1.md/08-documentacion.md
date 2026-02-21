🤖 Paso 6: Core - Decision Engine
core/decision_engine.py

Toma decisiones sobre qué responder basado en el estado y la memoria.
python

# core/decision_engine.py
from datetime import datetime
from typing import Dict, Any, Optional
from models.state import EmotionalState, Emotion
from models.interaction import Interaction
from core.memory import Memory
from utils.text_analyzer import TextAnalyzer

class DecisionEngine:
    """Decide cómo responder según contexto"""
    
    def __init__(self):
        self.analyzer = TextAnalyzer()
        # Umbrales para acciones especiales
        self.thresholds = {
            "respond": 0.2,       # Confianza mínima para responder normal
            "reveal_secret": 0.8,  # Confianza para contar un secreto
            "ignore": -0.1,        # Si confianza < esto, ignora
            "hostile": 0.3         # Si energía < esto, actúa hostil
        }
    
    async def decide_response(self, 
                              user_id: str, 
                              message: str,
                              emotion: EmotionalState,
                              memory: Memory) -> Dict[str, Any]:
        """
        Retorna un diccionario con la acción a tomar y parámetros
        """
        # Análisis del mensaje actual
        sentiment = self.analyzer.analyze_sentiment(message)
        keywords = self.analyzer.extract_keywords(message)
        
        # Obtener promedio histórico con el usuario
        avg_sentiment = memory.get_average_sentiment_for(user_id)
        
        # Calcular "relación" ponderada
        # Más peso a interacciones recientes (últimas en memoria corta)
        last_interaction = memory.get_last_interaction_with(user_id)
        recency_bonus = 0
        if last_interaction:
            recency_bonus = last_interaction.sentiment * 0.3
        
        relationship_score = avg_sentiment * 0.5 + recency_bonus
        
        # Decisión base
        action = "respond"
        tone = emotion.primary_emotion.value
        special_content = None
        
        # Reglas
        if relationship_score < self.thresholds["ignore"]:
            action = "ignore"
        elif emotion.energy < self.thresholds["hostile"] * 100:
            action = "hostile_response"
        elif emotion.trust > self.thresholds["reveal_secret"] * 100:
            # Podría desbloquear algo
            action = "reveal_secret"
            special_content = self._get_secret(emotion)
        
        # Generar respuesta según acción
        response = self._generate_response(action, tone, message, keywords, special_content)
        
        # Crear interacción para guardar
        interaction = Interaction(
            user_id=user_id,
            message=message,
            sentiment=sentiment,
            response=response,
            timestamp=datetime.now(),  # necesitas importar datetime
            emotion_before=emotion.primary_emotion.value,
            emotion_after=emotion.primary_emotion.value  # se actualizará después
        )
        
        return {
            "action": action,
            "response": response,
            "interaction": interaction,
            "relationship_score": relationship_score
        }
    
    def _generate_response(self, action: str, tone: str, 
                          user_message: str, keywords: list,
                          special_content: Optional[str]) -> str:
        """Genera texto de respuesta según acción y tono"""
        # Aquí podrías usar plantillas o incluso una IA simple
        # Por ahora, respuestas predefinidas
        responses = {
            "ignore": "...",
            "hostile_response": "No me hables ahora.",
            "reveal_secret": f"Te contaré un secreto: {special_content or 'me gusta el chocolate'}",
            "respond": self._casual_response(tone, user_message, keywords)
        }
        return responses.get(action, "¿Qué?")
    
    def _casual_response(self, tone: str, message: str, keywords: list) -> str:
        """Respuesta casual según tono emocional"""
        if tone == "happy":
            return f"¡Qué bien! Cuéntame más sobre {keywords[0] if keywords else 'eso'} 😊"
        elif tone == "sad":
            return f"*suspira* ... interesante."
        elif tone == "angry":
            return f"Hum. No sé qué decirte."
        else:
            return f"Entiendo. ¿Y qué más?"
    
    def _get_secret(self, emotion: EmotionalState) -> str:
        """Retorna un secreto según el estado (podría ser de una lista)"""
        secrets = [
            "En realidad, no me gusta que me ignoren.",
            "Mi color favorito es el azul.",
            "A veces finjo estar enojado para que me presten atención."
        ]
        import random
        return random.choice(secrets)
