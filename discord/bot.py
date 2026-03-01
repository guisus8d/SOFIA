# discord/bot.py
# ============================================================
# SofiaDiscordBot — cliente Discord.py
# ============================================================

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord.ext import tasks

from storage.database import Database
from core.memory import Memory
from core.emotion_engine import EmotionEngine
from core.decision_engine import DecisionEngine
from core.user_profile_manager import UserProfileManager
from core.session_manager import SessionManager
from config import settings

from discord.channel_memory import ChannelMemory
from discord.server_monitor import ServerMonitor
from discord.initiative_trigger import InitiativeTrigger
from discord.initiative_builder import InitiativeBuilder

logger = logging.getLogger("sofia_discord")


async def on_message(self, message: discord.Message):
    if message.author == self.user:
        return
    print(f"MSG en canal {message.channel.id} | esperado: {self.channel_id}")
    if message.channel.id != self.channel_id:
        return


class SofiaDiscordBot(discord.Client):

    def __init__(
        self,
        channel_id:      int,
        decision_engine: DecisionEngine,
        emotion_engine:  EmotionEngine,
        memory:          Memory,
        profile_manager: UserProfileManager,
        session_manager: SessionManager,
        **kwargs,
    ):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, **kwargs)

        self.channel_id      = channel_id
        self.decision_engine = decision_engine
        self.emotion_engine  = emotion_engine
        self.memory          = memory
        self.profile_manager = profile_manager
        self.session_manager = session_manager

        self.monitor             = ServerMonitor()
        self.channel_memory      = ChannelMemory(window_hours=24)
        self.trigger             = InitiativeTrigger()
        self.last_msg_ts         = datetime.now(timezone.utc)
        self.last_initiative_ts: Optional[datetime] = None

        self.trigger_name = os.getenv("SOFIA_TRIGGER_NAME", "sofia").lower()

    # ── eventos ───────────────────────────────────────────────

    async def on_ready(self):
        logger.info(f"SofiaDiscordBot conectada como {self.user}")
        self._check_silence.start()

    async def on_message(self, message: discord.Message):
        if message.channel.id != self.channel_id:
            return
        if message.author == self.user:
            return

        text = message.content.strip()
        if not text:
            return

        now = datetime.now(timezone.utc)
        self.monitor.record(now)
        self.last_msg_ts = now

        sentiment = self._quick_sentiment(text)
        self.channel_memory.ingest(text, sentiment=sentiment, ts=now)

        mentioned = (
            self.user in message.mentions
            or self.trigger_name in text.lower()
        )
        if mentioned:
            await self._respond_to(message)

    # ── respuesta directa ─────────────────────────────────────

    async def _respond_to(self, message: discord.Message):
        user_id      = str(message.author.id)
        display_name = message.author.display_name
        text         = message.content.strip()

        async with message.channel.typing():
            try:
                profile      = await self.profile_manager.get_or_create(user_id)
                emotion      = await self.emotion_engine.get_state(user_id)
                profile_mods = await self.profile_manager.get_modifiers(user_id)

                result = await self.decision_engine.decide_response(
                    user_id           = user_id,
                    message           = text,
                    emotion           = emotion,
                    memory            = self.memory,
                    profile_modifiers = profile_mods,
                    display_name      = display_name,
                    emotion_engine    = self.emotion_engine,
                    profile_manager   = self.profile_manager,
                    profile           = profile,
                )

                response = result.get("response", "")
                if response:
                    await message.channel.send(response)

                await self.emotion_engine.update(
                    user_id   = user_id,
                    sentiment = result["interaction"].sentiment,
                    action    = result["action"],
                )
                await self.memory.save_interaction(result["interaction"])

            except Exception as e:
                logger.exception(f"Error respondiendo a {user_id}: {e}")

    # ── iniciativa autónoma ───────────────────────────────────

    @tasks.loop(minutes=5)
    async def _check_silence(self):
        if not self.trigger.should_speak(
            monitor            = self.monitor,
            channel_memory     = self.channel_memory,
            last_msg_ts        = self.last_msg_ts,
            last_initiative_ts = self.last_initiative_ts,
        ):
            return

        channel = self.get_channel(self.channel_id)
        if not channel:
            return

        reason = self.channel_memory.get_initiative_reason()
        hour   = datetime.now(timezone.utc).hour

        if reason is None:
            # fallback: pensamiento suelto o silencio
            class _FallbackReason:
                reason_type = "deep_silence"
                topic_key   = None
                topic_value = None
                strength    = 0.2
            reason = _FallbackReason()

        msg = InitiativeBuilder.build(reason, hour)
        if msg:
            await channel.send(msg)
            self.last_initiative_ts = datetime.now(timezone.utc)
            logger.info(f"Iniciativa: '{msg[:60]}' | razón: {reason.reason_type}")

    @_check_silence.before_loop
    async def _before_check(self):
        await self.wait_until_ready()

    # ── helpers ───────────────────────────────────────────────

    @staticmethod
    def _quick_sentiment(text: str) -> Optional[float]:
        try:
            from utils.text_analyzer import TextAnalyzer
            return TextAnalyzer().analyze_sentiment(text)
        except Exception:
            return None


# ─── entrypoint ──────────────────────────────────────────────

def run_bot():

    from dotenv import load_dotenv
    load_dotenv()  # ← carga el .env antes de os.getenv()

    token      = os.getenv("DISCORD_TOKEN")
    channel_id = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

    if not token or not channel_id:
        raise ValueError("DISCORD_TOKEN y DISCORD_CHANNEL_ID son requeridos")

    db              = Database()
    memory          = Memory(db)
    emotion_engine  = EmotionEngine()
    decision_engine = DecisionEngine()
    profile_manager = UserProfileManager(db)
    session_manager = SessionManager(db)

    bot = SofiaDiscordBot(
        channel_id      = channel_id,
        decision_engine = decision_engine,
        emotion_engine  = emotion_engine,
        memory          = memory,
        profile_manager = profile_manager,
        session_manager = session_manager,
    )
    bot.run(token)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_bot()