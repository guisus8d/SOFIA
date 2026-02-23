# main.py
# ============================================================
# SocialBot v0.5.0 — Memoria Episódica
# Cambios:
#   - Integra SessionManager al arrancar y al cerrar
#   - Sofía saluda según el historial del usuario
#   - Al escribir 'salir' guarda la sesión automáticamente
# ============================================================

import asyncio
from utils.logger import logger
from storage.database import Database
from core.memory import Memory
from core.emotion_engine import EmotionEngine
from core.decision_engine import DecisionEngine
from core.user_profile_manager import UserProfileManager
from core.session_manager import SessionManager
from config import settings


class SocialBot:
    def __init__(self):
        self.db              = Database(str(settings.DATABASE_PATH))
        self.memory          = Memory(self.db)
        self.profile_manager = UserProfileManager(self.db)
        self.emotion_engine  = EmotionEngine()
        self.decision        = DecisionEngine()
        self.session_manager = SessionManager(self.db)   # 🆕
        logger.info("Bot inicializado.")

    async def process_message(self, user_id: str, message: str) -> str:
        logger.info(f"Mensaje de {user_id}: {message}")

        profile   = await self.profile_manager.get_or_create_profile(user_id)
        modifiers = self.profile_manager.get_behavior_modifiers(profile)

        decision = await self.decision.decide_response(
            user_id=user_id,
            message=message,
            emotion=profile.emotional_state,
            memory=self.memory,
            profile_modifiers=modifiers
        )

        interaction      = decision["interaction"]
        repair_multiplier = self.decision.analyzer.get_repair_multiplier(message)

        new_state = await self.emotion_engine.process_interaction_for_state(
            state=profile.emotional_state,
            interaction=interaction,
            memory=self.memory,
            repair_multiplier=repair_multiplier,
            relationship_damage=profile.relationship_damage
        )

        interaction.emotion_after  = new_state.primary_emotion.value
        profile.emotional_state    = new_state

        await self.memory.remember(interaction)
        await self.profile_manager.update_profile_from_interaction(profile, interaction)

        return decision["response"]

    async def run_cli(self):
        print(f"\n--- {settings.BOT_NAME} v{settings.VERSION} ---")
        print("Escribe 'salir' para terminar.\n")

        user_id = "test_user_1"

        # 🆕 Saludo con memoria episódica
        greeting = self.session_manager.get_greeting(user_id)
        print(f"Sofía: {greeting}\n")

        while True:
            user_input = input("Tú: ")
            if user_input.lower() in ["salir", "exit", "quit"]:
                # 🆕 Guardar sesión al cerrar
                profile = await self.profile_manager.get_or_create_profile(user_id)
                self.session_manager.save_session(user_id, profile)
                print("Sofía: ¡Hasta luego! 😊")
                break

            response = await self.process_message(user_id, user_input)
            print(f"Sofía: {response}")

            profile = await self.profile_manager.get_or_create_profile(user_id)
            estado  = profile.emotional_state
            print(f"[{estado.primary_emotion.value} | energía:{estado.energy:.1f} confianza:{estado.trust:.1f} daño:{profile.relationship_damage:.2f}]\n")


async def main():
    bot = SocialBot()
    await bot.run_cli()


if __name__ == "__main__":
    asyncio.run(main())