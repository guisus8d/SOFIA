# discord/server_agent.py
# ============================================================
# ServerAgent — Sofía como agente proactivo del servidor
# v2 — manda imágenes como archivo Discord (no embed URL)
# ============================================================

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from discord.ext import commands

logger = logging.getLogger("sofia_agent")

_MOD_ROLE_KEYWORDS = {"mod", "admin", "moderador", "moderator", "staff", "owner", "dueño"}
_INACTIVITY_DAYS   = 3

_WELCOME_MESSAGES = [
    "Oye {name}, bienvenide. Si quieres hablar ya sabes, por aquí ando.",
    "Hola {name}. Qué bueno que llegaste, espero que te sientas cómode acá.",
    "{name}, hola. Bienvenide al server, cualquier cosa me mencionas.",
    "Ah mira, llegó {name}. Bienvenide, espero que disfrutes el server.",
]

_MOD_INTRO_MESSAGES = [
    "Oye {name}, veo que eres {role}. Si alguna vez necesitas banear a alguien con clase o hacer un anuncio bonito, me avisas jeje.",
    "Hola {name}. Soy Sofía, puedo ayudarte con bienvenidas, anuncios y hasta moderar un poco si me lo pides. Solo dime.",
    "{name} 👀 Sé que eres {role}. Puedo generar avatares para los nuevos, hacer anuncios más humanos, o simplemente hablar. Aquí estoy.",
]

_REACTIVATION_MESSAGES = [
    "Oye {name}, hace rato que no sé nada de ti. ¿Todo bien por ahí?",
    "{name}... llevas un tiempo sin aparecer. ¿Qué has estado haciendo?",
    "Hey {name}, ¿sigues vivo/a? jeje. Solo quería saber cómo estás.",
]

_THINKING_MESSAGES = [
    "Espera, déjame imaginar cómo serías...",
    "A ver, pensando cómo hacerte jeje...",
    "Mmm, déjame crear algo para ti.",
    "Dame un momento...",
]

_AVATAR_REVEAL_MESSAGES = [
    "Así te imaginé, {name}.",
    "No sé, creo que esto te va, {name}.",
    "Qué tal este avatar, {name}?",
    "Aquí está, {name}. ¿Qué te parece?",
]


class ServerAgent:

    def __init__(self, bot, memory, profile_manager, avatar_generator):
        self.bot             = bot
        self.memory          = memory
        self.profile_manager = profile_manager
        self.avatar          = avatar_generator

        self._mod_introduced: set[str] = set()
        self._welcomed:       set[str] = set()
        # Trackea última acción por usuario para contexto
        self.last_action:     dict[str, str] = {}

    # ----------------------------------------------------------
    # BIENVENIDA CON AVATAR
    # ----------------------------------------------------------

    async def welcome_member(self, member: discord.Member):
        if str(member.id) in self._welcomed:
            return
        self._welcomed.add(str(member.id))

        channel = member.guild.system_channel or next(
            (c for c in member.guild.text_channels
             if c.permissions_for(member.guild.me).send_messages),
            None
        )
        if not channel:
            return

        msg = random.choice(_WELCOME_MESSAGES).format(name=member.display_name)

        # Intentar generar avatar
        img_bytes, filename = await self.avatar.fetch_image(
            user_id=str(member.id),
            display_name=member.display_name,
            profile=None,
        )

        if img_bytes:
            file = discord.File(img_bytes, filename=filename)
            embed = discord.Embed(description=msg, color=0x7289DA)
            embed.set_image(url=f"attachment://{filename}")
            embed.set_footer(text="Avatar generado especialmente para ti ✨")
            await channel.send(content=member.mention, file=file, embed=embed)
        else:
            await channel.send(f"{member.mention} {msg}")

    # ----------------------------------------------------------
    # INTRO A MODERADORES
    # ----------------------------------------------------------

    async def check_mod_intro(self, message: discord.Message):
        if not hasattr(message.author, "roles"):
            return

        user_id = str(message.author.id)
        if user_id in self._mod_introduced:
            return

        mod_role = next(
            (r for r in message.author.roles
             if any(kw in r.name.lower() for kw in _MOD_ROLE_KEYWORDS)),
            None
        )
        if not mod_role:
            return

        self._mod_introduced.add(user_id)
        await asyncio.sleep(random.uniform(1.5, 3.0))

        intro = random.choice(_MOD_INTRO_MESSAGES).format(
            name=message.author.display_name,
            role=mod_role.name,
        )
        try:
            await message.channel.send(intro)
        except Exception as e:
            logger.warning(f"No pude intro a mod: {e}")

    # ----------------------------------------------------------
    # GENERAR AVATAR (comando o conversación)
    # ----------------------------------------------------------

    async def generate_avatar_for(
        self,
        user_id: str,
        display_name: str,
        channel: discord.abc.Messageable,
        subject: Optional[str] = None,
    ):
        self.last_action[user_id] = "avatar"

        thinking_msg = await channel.send(random.choice(_THINKING_MESSAGES))

        try:
            profile = await self.profile_manager.get_or_create_profile(user_id)
        except Exception:
            profile = None

        img_bytes, filename = await self.avatar.fetch_image(
            user_id=user_id,
            display_name=display_name,
            profile=profile,
            subject=subject,
        )

        await thinking_msg.delete()

        if not img_bytes:
            await channel.send("No pude generar la imagen ahora, Pollinations tardó demasiado. Intenta de nuevo.")
            return

        reveal = random.choice(_AVATAR_REVEAL_MESSAGES).format(name=display_name)
        file   = discord.File(img_bytes, filename=filename)
        embed  = discord.Embed(description=reveal, color=0x5865F2)
        embed.set_image(url=f"attachment://{filename}")

        if subject:
            embed.set_footer(text=f"Estilo: {subject} ✨")
        else:
            embed.set_footer(text="Generado con tu personalidad ✨")

        await channel.send(file=file, embed=embed)

    # ----------------------------------------------------------
    # LOOP DE REACTIVACIÓN
    # ----------------------------------------------------------

    async def start_reactivation_loop(self):
        await self.bot.wait_until_ready()
        logger.info("🔄 ServerAgent: loop de reactivación iniciado")

        while not self.bot.is_closed():
            try:
                await self._check_inactive_users()
            except Exception as e:
                logger.warning(f"Error en reactivation loop: {e}")
            await asyncio.sleep(6 * 60 * 60)

    async def _check_inactive_users(self):
        cutoff = datetime.now() - timedelta(days=_INACTIVITY_DAYS)

        for guild in self.bot.guilds:
            for member in guild.members:
                if member.bot:
                    continue
                user_id = str(member.id)
                try:
                    profile = await self.profile_manager.get_or_create_profile(user_id)
                except Exception:
                    continue

                if profile.interaction_count < 3:
                    continue

                last_seen = profile.last_seen
                if not last_seen:
                    continue
                if isinstance(last_seen, str):
                    try:
                        last_seen = datetime.fromisoformat(last_seen)
                    except Exception:
                        continue

                if last_seen < cutoff:
                    await self._send_reactivation(member, profile)
                    await asyncio.sleep(30)

    async def _send_reactivation(self, member: discord.Member, profile):
        msg = random.choice(_REACTIVATION_MESSAGES).format(name=member.display_name)
        try:
            dm = await member.create_dm()
            await dm.send(msg)
            logger.info(f"Reactivación enviada a {member.display_name}")
        except discord.Forbidden:
            pass
        except Exception as e:
            logger.warning(f"No pude reactivar a {member.display_name}: {e}")