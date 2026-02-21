🎮 Paso 8: Main - CLI de prueba
main.py

Punto de entrada con bucle de consola para probar.
python

# main.py
import asyncio
from datetime import datetime
from utils.logger import logger
from utils.text_analyzer import TextAnalyzer
from storage.database import Database
from core.memory import Memory
from core.emotion_engine import EmotionEngine
from core.decision_engine import DecisionEngine
from models.state import EmotionalState
from config import settings

class SocialBot:
    def __init__(self):
        self.db = Database(str(settings.DATABASE_PATH))
        self.memory = Memory(self.db)
        # Cargar último estado emocional
        saved_state = self.db.load_emotional_state()
        self.emotion = EmotionEngine(saved_state)
        self.decision = DecisionEngine()
        self.analyzer = TextAnalyzer()
        logger.info(f"Bot inicializado. Estado: {self.emotion.state.primary_emotion.value}")
    
    async def process_message(self, user_id: str, message: str) -> str:
        """Procesa un mensaje y retorna respuesta"""
        logger.info(f"Mensaje de {user_id}: {message}")
        
        # Decidir respuesta
        decision = await self.decision.decide_response(
            user_id, message, self.emotion.state, self.memory
        )
        
        interaction = decision["interaction"]
        
        # Actualizar emoción con esta interacción
        new_state = await self.emotion.process_interaction(interaction, self.memory)
        
        # Actualizar la emoción final en la interacción
        interaction.emotion_after = new_state.primary_emotion.value
        
        # Guardar en memoria
        await self.memory.remember(interaction)
        
        # Guardar estado en BD
        self.db.save_emotional_state(new_state)
        
        return decision["response"]
    
    async def run_cli(self):
        """Bucle de consola para pruebas"""
        print(f"\n--- {settings.BOT_NAME} v{settings.VERSION} ---")
        print("Escribe 'salir' para terminar.\n")
        
        user_id = "test_user_1"  # Usuario fijo para prueba
        
        while True:
            user_input = input("Tú: ")
            if user_input.lower() in ["salir", "exit", "quit"]:
                break
            
            response = await self.process_message(user_id, user_input)
            print(f"Bot: {response}")
            
            # Mostrar estado actual (debug)
            estado = self.emotion.state
            print(f"[{estado.primary_emotion.value} | energía:{estado.energy:.1f} confianza:{estado.trust:.1f}]\n")

async def main():
    bot = SocialBot()
    await bot.run_cli()

if __name__ == "__main__":
    asyncio.run(main())