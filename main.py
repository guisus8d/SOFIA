# discord_bot.py
# ============================================================
# SocialBot v0.9.3
# CAMBIOS vs v0.9.2:
#   - NUEVO: Mini-embed de estado visible después de CADA mensaje
#     de Sofía (no solo con !estado). Barras de energía/confianza/daño
#     en tiempo real para debugging visual permanente.
#   - process_message ahora retorna dict con response + profile
#     para poder construir el embed inline.
# ============================================================

import asyncio
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
# HELPERS VISUALES
# ============================================================

def _bar(value: float, max_val: float = 100.0, length: int = 10) -> str:
    """Barra de progreso Unicode. Ej: ████░░░░░░"""
    filled = round((min(max(value, 0), max_val) / max_val) * length)
    return "█" * filled + "░" * (length - filled)

def _emotion_emoji(emo_value: str) -> str:
    return {
        "happy":   "😊",
        "neutral": "😐",
        "sad":     "😔",
        "angry":   "😠",
        "fearful": "😰",
    }.get(emo_value, "😐")

def _energy_color(energy: float, trust: float, emo: str) -> discord.Color:
    if emo == "happy":   return discord.Color.from_rgb(100, 200, 120)
    if emo == "angry":   return discord.Color.from_rgb(210, 70,  70)
    if emo == "sad":     return discord.Color.from_rgb(90,  120, 200)
    if emo == "fearful": return discord.Color.from_rgb(170, 120, 210)
    if energy > 60 and trust > 60:
        return discord.Color.from_rgb(100, 190, 210)
    return discord.Color.from_rgb(140, 140, 140)

def _conflict_status(user_id: str) -> tuple[str, str]:
    """Retorna (icono, texto) del estado de conflicto."""
    agg = decision.aggression_count.get(user_id, 0)
    rec = decision.recovery_needed.get(user_id, 0)
    if agg >= 5:
        return "🚫", f"Bloqueada ({agg} agresiones)"
    if agg > 0 and rec > 0:
        return "🔄", f"Recovery — {rec} msgs restantes"
    if agg > 0:
        return "⚠️", f"Conflicto ({agg} agresiones)"
    return "✅", "Normal"

def build_mini_embed(profile, user_id: str, action: str) -> discord.Embed:
    """
    Embed compacto que se muestra debajo de CADA respuesta de Sofía.
    Muestra energía, confianza, daño y estado de conflicto en tiempo real.
    """
    e       = profile.emotional_state
    emo_val = e.primary_emotion.value
    dmg     = profile.relationship_damage
    dmg_pct = min(dmg * 10, 100)

    icon, conflict_txt = _conflict_status(user_id)

    # Energía: color de barra según nivel
    energy_bar  = _bar(e.energy)
    trust_bar   = _bar(e.trust)
    dmg_bar     = _bar(dmg_pct)

    # Etiqueta de acción tomada
    action_labels = {
        "respond":       "💬 responder",
        "boundary":      "🛑 límite",
        "silence":       "🤐 silencio",
        "limit":         "🚫 bloqueo",
        "recovery":      "🔄 recovery",
        "memory_check":  "🧠 memoria",
        "opinion":       "💭 opinión",
        "ignore":        "👁️ ignorar",
        "identity":      "🪞 identidad",
        "direct_answer": "🎯 respuesta directa",
        "initiative":    "✨ iniciativa",
        "repeat":        "🔁 repetición",
    }
    action_txt = action_labels.get(action, f"• {action}")

    # Trust como nivel de relación legible
    if e.trust >= 75:    rel = "Alta 💚"
    elif e.trust >= 50:  rel = "Media 💛"
    elif e.trust >= 30:  rel = "Baja 🧡"
    else:                rel = "Rota ❤️‍🔥"

    embed = discord.Embed(color=_energy_color(e.energy, e.trust, emo_val))
    embed.add_field(
        name=f"{_emotion_emoji(emo_val)} Sofía interna",
        value=(
            f"⚡ `{energy_bar}` {e.energy:.0f}\n"
            f"💙 `{trust_bar}` {e.trust:.0f}\n"
            f"💔 `{dmg_bar}` daño {dmg:.1f}"
        ),
        inline=True,
    )
    embed.add_field(
        name="📊 Relación",
        value=(
            f"Vínculo: {rel}\n"
            f"{icon} {conflict_txt}\n"
            f"Acción: {action_txt}"
        ),
        inline=True,
    )
    embed.set_footer(text=f"emoción: {emo_val}  ·  !estado para detalle completo  ·  !reset para limpiar")
    return embed


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

    # 1. Respuesta de texto de Sofía
    await message.reply(result["response"])

    # 2. Mini-embed de estado justo debajo (en el mismo canal, no como reply)
    mini = build_mini_embed(result["profile"], user_id, result["action"])
    await message.channel.send(embed=mini)

    await bot.process_commands(message)


# ============================================================
# PROCESAR MENSAJE — ahora retorna dict
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
    """!reset — resetea contadores de sesión (testing)"""
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
    """!estado — embed completo con todo el detalle interno"""
    user_id     = str(ctx.author.id)
    profile     = await profile_manager.get_or_create_profile(user_id)
    e           = profile.emotional_state
    emo_val     = e.primary_emotion.value
    mood_reason = emotion_engine.get_mood_reason(user_id) or "sin razón particular"
    night_mode  = emotion_engine.is_night_mode()
    dmg         = profile.relationship_damage
    dmg_pct     = min(dmg * 10, 100)

    agg = decision.aggression_count.get(user_id, 0)
    rec = decision.recovery_needed.get(user_id, 0)
    icon, conflict_txt = _conflict_status(user_id)

    embed = discord.Embed(
        title=f"{_emotion_emoji(emo_val)}  Estado completo de Sofía",
        description=f"Usuario: **{ctx.author.display_name}** · emoción: `{emo_val.upper()}`",
        color=_energy_color(e.energy, e.trust, emo_val),
    )
    embed.add_field(name="⚡ Energía",         value=f"`{_bar(e.energy, length=14)}` **{e.energy:.1f}/100**",  inline=False)
    embed.add_field(name="💙 Confianza",        value=f"`{_bar(e.trust,  length=14)}` **{e.trust:.1f}/100**",   inline=False)
    embed.add_field(name="💔 Daño relacional",  value=f"`{_bar(dmg_pct,  length=14)}` **{dmg:.2f}** (raw)",     inline=False)
    embed.add_field(name="🧠 Razón del estado", value=f"_{mood_reason}_",                                        inline=False)
    embed.add_field(name="📋 Conflicto",        value=f"{icon} {conflict_txt}",     inline=True)
    embed.add_field(name="🌙 Modo noche",       value="Sí" if night_mode else "No", inline=True)
    embed.add_field(name="💬 Frases guardadas", value=str(len(profile.important_quotes)), inline=True)

    sem = getattr(profile, "semantic_facts", {})
    if sem:
        facts_preview = "\n".join(f"`{k}`: {v}" for k, v in list(sem.items())[:6])
        embed.add_field(name="🗂️ Lo que sé de ti", value=facts_preview, inline=False)
    else:
        embed.add_field(name="🗂️ Lo que sé de ti", value="_Nada guardado aún_", inline=False)

    embed.set_footer(text=f"SocialBot {settings.VERSION} · !reset para limpiar contadores")
    await ctx.send(embed=embed)


# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    if not TOKEN:
        print("❌ No encontré el token. Crea un .env con DISCORD_TOKEN=tu_token")
    else:
        bot.run(TOKEN)