# main.py
# ============================================================
# SocialBot v0.10.0
# ============================================================

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.logger import logger
from storage.database import Database
from core.memory import Memory
from core.emotion_engine import EmotionEngine
from core.decision_engine import DecisionEngine
from core.user_profile_manager import UserProfileManager
from core.session_manager import SessionManager
from config import settings

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

db              = Database(str(settings.DATABASE_PATH))
memory          = Memory(db)
profile_manager = UserProfileManager(db)
emotion_engine  = EmotionEngine()
decision        = DecisionEngine()
session_manager = SessionManager(db)


# ============================================================
# EVENTOS
# ============================================================

@bot.event
async def on_ready():
    logger.info(f"Sofía conectada como {bot.user}")
    print(f"\n✅ Sofía está en línea como {bot.user} (v{settings.VERSION})\n")


@bot.event
async def on_member_join(member):
    channel = member.guild.system_channel
    if channel:
        greeting = session_manager.get_greeting(str(member.id))
        await channel.send(f"{member.mention} {greeting}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.author.bot:
        return

    is_dm      = isinstance(message.channel, discord.DMChannel)
    is_mention = bot.user in message.mentions

    if not is_dm and not is_mention:
        return

    content = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not content:
        content = "hola"

    user_id      = str(message.author.id)
    display_name = message.author.display_name

    async with message.channel.typing():
        result = await process_message(user_id, content, display_name)

    await message.reply(result["response"])
    await bot.process_commands(message)


# ============================================================
# PROCESAR MENSAJE
# ============================================================

async def process_message(user_id: str, message: str, display_name: str = "tú") -> dict:
    logger.info(f"Mensaje de {display_name} ({user_id}): {message}")

    profile   = await profile_manager.get_or_create_profile(user_id)
    modifiers = profile_manager.get_behavior_modifiers(profile)

    decision_result = await decision.decide_response(
        user_id=user_id,
        message=message,
        emotion=profile.emotional_state,
        memory=memory,
        profile_modifiers=modifiers,
        display_name=display_name,
        emotion_engine=emotion_engine,
        profile_manager=profile_manager,
        profile=profile,
    )

    interaction       = decision_result["interaction"]
    repair_multiplier = decision.analyzer.get_repair_multiplier(message)

    aggression_impact = None
    if decision_result["action"] in ("boundary", "silence", "limit"):
        agg = decision.aggression_detector.detect(
            message, trust=profile.emotional_state.trust
        )
        if agg["detected"]:
            aggression_impact = agg["impact"]

    new_state = await emotion_engine.process_interaction_for_state(
        state=profile.emotional_state,
        interaction=interaction,
        memory=memory,
        repair_multiplier=repair_multiplier,
        relationship_damage=profile.relationship_damage,
        aggression_impact=aggression_impact,
    )

    interaction.emotion_after = new_state.primary_emotion.value
    profile.emotional_state   = new_state

    await memory.remember(interaction)
    await profile_manager.update_profile_from_interaction(profile, interaction)

    return {
        "response": decision_result["response"],
        "action":   decision_result["action"],
        "profile":  profile,
    }


# ============================================================
# COMANDOS
# ============================================================

@bot.command(name="sofia")
async def sofia_info(ctx):
    await ctx.send(
        f"Soy Sofía 😊\n"
        f"Versión: `{settings.VERSION}`\n"
        f"Creada por: `JesusJM`\n"
        f"Mencióname o escríbeme por DM para hablar."
    )


@bot.command(name="reset")
async def reset_cmd(ctx):
    user_id = str(ctx.author.id)
    decision.aggression_count.pop(user_id, None)
    decision.recovery_needed.pop(user_id, None)
    decision.short_streak.pop(user_id, None)
    decision.secrets_revealed.pop(user_id, None)
    decision._secrets_date.pop(user_id, None)
    decision._topic_question_history.pop(user_id, None)
    decision._output_cooldowns.pop(user_id, None)
    decision._msg_counter.pop(user_id, None)
    await ctx.send("🔄 Contadores reseteados.")


@bot.command(name="estado")
async def estado_cmd(ctx):
    user_id     = str(ctx.author.id)
    profile     = await profile_manager.get_or_create_profile(user_id)
    e           = profile.emotional_state
    emo_val     = e.primary_emotion.value
    mood_reason = emotion_engine.get_mood_reason(user_id) or "sin razón particular"
    night_mode  = emotion_engine.is_night_mode()
    dmg         = profile.relationship_damage

    agg = decision.aggression_count.get(user_id, 0)
    rec = decision.recovery_needed.get(user_id, 0)

    if agg >= 5:
        conflict = f"🚫 Bloqueada ({agg} agresiones)"
    elif agg > 0 and rec > 0:
        conflict = f"🔄 Recovery — {rec} msgs restantes"
    elif agg > 0:
        conflict = f"⚠️ Conflicto ({agg} agresiones)"
    else:
        conflict = "✅ Normal"

    sem = getattr(profile, "semantic_facts", {})
    facts_text = ""
    if sem:
        facts_text = "\n".join(f"  {k}: {v}" for k, v in list(sem.items())[:6])

    await ctx.send(
        f"**Estado de Sofía contigo**\n"
        f"Emoción: `{emo_val}` · Energía: `{e.energy:.0f}` · Confianza: `{e.trust:.0f}`\n"
        f"Daño relacional: `{dmg:.2f}` · Modo noche: `{'sí' if night_mode else 'no'}`\n"
        f"Estado: {conflict}\n"
        f"Razón: _{mood_reason}_\n"
        f"Frases guardadas: `{len(profile.important_quotes)}`"
        + (f"\nLo que sé de ti:\n{facts_text}" if facts_text else "")
    )


# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    if not TOKEN:
        print("❌ No encontré el token. Crea un .env con DISCORD_TOKEN=tu_token")
    else:
        bot.run(TOKEN)