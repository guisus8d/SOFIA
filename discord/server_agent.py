# discord/server_agent.py
# ============================================================
# ServerAgent — Sofía como agente proactivo del servidor
# Actúa desde su personalidad, no como bot de comandos.
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

# IDs de roles que se consideran moderadores/admins
# Sofía los detecta por nombre de rol, sin hardcodear IDs
_MOD_ROLE_KEYWORDS = {"mod", "admin", "moderador", "moderator", "staff", "owner", "dueño"}

# Cuántos días sin interacción antes de que Sofía mande un mensaje espontáneo
_INACTIVITY_DAYS = 3

# Mensajes de bienvenida — variados para que no suene robótico
_WELCOME_MESSAGES = [
    "Oye {name}, bienvenide. Si quieres hablar ya sabes, por aquí ando.",
    "Hola {name}. Qué bueno que llegaste, espero que te sientas cómode acá.",
    "{name}, hola. Bienvenide al server, cualquier cosa me mencionas.",
    "Ah mira, llegó {name}. Bienvenide, espero que disfrutes el server.",
]

# Mensajes cuando detecta a un mod por primera vez
_MOD_INTRO_MESSAGES = [
    "Oye {name}, veo que eres {role}. Si alguna vez necesitas banear a alguien con clase o hacer un anuncio bonito, me avisas jeje.",
    "Hola {name}. Soy Sofía, puedo ayudarte con bienvenidas, anuncios y hasta moderar un poco si me lo pides. Solo dime.",
    "{name} 👀 Sé que eres {role}. Puedo generar avatares para los nuevos, hacer anuncios más humanos, o simplemente hablar. Aquí estoy.",
]

# Mensajes de reactivación espontánea
_REACTIVATION_MESSAGES = [
    "Oye {name}, hace rato que no sé nada de ti. ¿Todo bien por ahí?",
    "{name}... llevas un tiempo sin aparecer. ¿Qué has estado haciendo?",
    "Hey {name}, ¿sigues vivo/a? jeje. Solo quería saber cómo estás.",
]


class ServerAgent:

    def __init__(self, bot: "commands.Bot", memory, profile_manager, avatar_generator):
        self.bot             = bot
        self.memory          = memory
        self.profile_manager = profile_manager
        self.avatar          = avatar_generator

        # Track a quién ya le presentamos las capacidades
        self._mod_introduced:  set[str] = set()
        self._welcomed:        set[str] = set()

    # ----------------------------------------------------------
    # BIENVENIDA MEJORADA
    # ----------------------------------------------------------

    async def welcome_member(self, member: discord.Member):
        """
        Bienvenida humanizada con avatar generado personalizado.
        Se llama desde on_member_join en main.py.
        """
        if str(member.id) in self._welcomed:
            return
        self._welcomed.add(str(member.id))

        channel = member.guild.system_channel
        if not channel:
            # Buscar cualquier canal de texto disponible
            channel = next(
                (c for c in member.guild.text_channels
                 if c.permissions_for(member.guild.me).send_messages),
                None
            )
        if not channel:
            return

        # Mensaje de bienvenida natural
        msg = random.choice(_WELCOME_MESSAGES).format(name=member.display_name)

        # Generar avatar personalizado (perfil vacío por ahora, se llenará con el tiempo)
        try:
            avatar_url = await self.avatar.generate_for_user(
                user_id=str(member.id),
                display_name=member.display_name,
                profile=None,
            )

            # Pre-cargar la imagen
            await self.avatar.preload(avatar_url)

            embed = discord.Embed(
                description=msg,
                color=0x7289DA,
            )
            embed.set_image(url=avatar_url)
            embed.set_footer(text="Este avatar fue generado especialmente para ti ✨")

            await channel.send(content=member.mention, embed=embed)

        except Exception as e:
            logger.warning(f"No pude generar avatar para {member.display_name}: {e}")
            # Fallback sin imagen
            await channel.send(f"{member.mention} {msg}")

    # ----------------------------------------------------------
    # DETECCIÓN DE MODERADORES
    # ----------------------------------------------------------

    async def check_mod_intro(self, message: discord.Message):
        """
        Detecta si quien habla es mod/admin y si Sofía aún no se presentó.
        Se llama desde on_message en main.py.
        """
        if not hasattr(message.author, "roles"):
            return

        user_id = str(message.author.id)
        if user_id in self._mod_introduced:
            return

        # Buscar rol de moderación
        mod_role = None
        for role in message.author.roles:
            if any(kw in role.name.lower() for kw in _MOD_ROLE_KEYWORDS):
                mod_role = role
                break

        if not mod_role:
            return

        self._mod_introduced.add(user_id)

        # Esperar un momento para que no suene automático
        await asyncio.sleep(random.uniform(1.5, 3.0))

        intro = random.choice(_MOD_INTRO_MESSAGES).format(
            name=message.author.display_name,
            role=mod_role.name,
        )

        try:
            await message.channel.send(intro)
        except Exception as e:
            logger.warning(f"No pude enviar intro a mod {message.author.display_name}: {e}")

    # ----------------------------------------------------------
    # TAREA DE REACTIVACIÓN (background loop)
    # ----------------------------------------------------------

    async def start_reactivation_loop(self):
        """
        Loop que corre en segundo plano y detecta usuarios inactivos.
        Sofía les manda un mensaje espontáneo si llevan +N días sin hablar.
        """
        await self.bot.wait_until_ready()
        logger.info("🔄 ServerAgent: loop de reactivación iniciado")

        while not self.bot.is_closed():
            try:
                await self._check_inactive_users()
            except Exception as e:
                logger.warning(f"Error en reactivation loop: {e}")

            # Chequear cada 6 horas
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

                # Solo usuarios con quienes Sofía ya habló (interaction_count > 0)
                if profile.interaction_count < 3:
                    continue

                last_seen = profile.last_seen
                if not last_seen:
                    continue

                # Parsear last_seen si es string
                if isinstance(last_seen, str):
                    try:
                        last_seen = datetime.fromisoformat(last_seen)
                    except Exception:
                        continue

                if last_seen < cutoff:
                    await self._send_reactivation(member, profile)
                    # Solo un usuario por ciclo para no spamear
                    await asyncio.sleep(30)

    async def _send_reactivation(self, member: discord.Member, profile):
        """Manda un mensaje espontáneo a un usuario inactivo via DM."""
        msg = random.choice(_REACTIVATION_MESSAGES).format(
            name=member.display_name
        )
        try:
            dm = await member.create_dm()
            await dm.send(msg)
            logger.info(f"Reactivación enviada a {member.display_name}")
        except discord.Forbidden:
            logger.debug(f"{member.display_name} tiene DMs cerrados")
        except Exception as e:
            logger.warning(f"No pude reactivar a {member.display_name}: {e}")

    # ----------------------------------------------------------
    # COMANDO: GENERAR AVATAR MANUALMENTE
    # ----------------------------------------------------------

    async def generate_avatar_for(
        self,
        user_id: str,
        display_name: str,
        channel: discord.abc.Messageable,
    ):
        """
        Genera y envía un avatar personalizado en el canal.
        Se puede llamar cuando el usuario lo pide naturalmente.
        """
        profile = await self.profile_manager.get_or_create_profile(user_id)

        # Mensaje previo de Sofía para que no parezca instantáneo
        thinking_msg = await channel.send(
            random.choice([
                "Espera, déjame imaginar cómo serías...",
                "A ver, pensando cómo hacerte jeje...",
                "Mmm, déjame crear algo para ti.",
            ])
        )

        try:
            avatar_url = await self.avatar.generate_for_user(
                user_id=user_id,
                display_name=display_name,
                profile=profile,
            )

            await self.avatar.preload(avatar_url)

            embed = discord.Embed(
                description=random.choice([
                    f"Así te imaginé, {display_name}.",
                    f"No sé, creo que esto te va, {display_name}.",
                    f"Qué tal este avatar, {display_name}?",
                ]),
                color=0x5865F2,
            )
            embed.set_image(url=avatar_url)
            embed.set_footer(text="Generado con Pollinations.ai ✨")

            await thinking_msg.delete()
            await channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Error generando avatar para {display_name}: {e}")
            await thinking_msg.edit(content="Algo salió mal al generar tu avatar, lo siento.")