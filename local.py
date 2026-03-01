# local.py
# ============================================================
# SocialBot v0.10.0 — Modo local / terminal
# Prueba a Sofía directamente desde la consola sin necesidad
# de Discord ni token. Ideal para probar respuestas, ajustar
# personalidad y depurar el decision engine.
#
# Uso:
#   python local.py
#   python local.py --user tu_nombre
#   python local.py --user tu_nombre --id 12345
# ============================================================

import asyncio
import argparse
import sys
from pathlib import Path

# Asegura que el root del proyecto esté en el path
sys.path.insert(0, str(Path(__file__).parent))

from storage.database import Database
from core.memory import Memory
from core.emotion_engine import EmotionEngine
from core.decision_engine import DecisionEngine
from core.user_profile_manager import UserProfileManager
from core.session_manager import SessionManager
from config import settings


# ── Colores ANSI para la terminal ────────────────────────────
SOFIA  = "\033[95m"   # magenta — Sofía habla
USER   = "\033[96m"   # cyan    — tú hablas
INFO   = "\033[90m"   # gris    — info de estado
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"


def _estado_line(profile, action: str) -> str:
    e   = profile.emotional_state
    emo = e.primary_emotion.value
    emojis = {"happy": "😊", "neutral": "😐", "sad": "😔", "angry": "😠", "fearful": "😰"}
    icon = emojis.get(emo, "😐")
    return (
        f"{INFO}  {icon} {emo} · "
        f"⚡{e.energy:.0f} 💙{e.trust:.0f} 💔{profile.relationship_damage:.1f} "
        f"· [{action}]{RESET}"
    )


def _print_header(user_name: str):
    print(f"\n{BOLD}{'─'*52}{RESET}")
    print(f"{BOLD}  SocialBot {settings.VERSION} — Modo Local{RESET}")
    print(f"  Hablando con Sofía como: {BOLD}{user_name}{RESET}")
    print(f"  Escribe {BOLD}!salir{RESET} para terminar · {BOLD}!reset{RESET} para limpiar estado")
    print(f"  {BOLD}!estado{RESET} para ver el estado completo")
    print(f"{'─'*52}{RESET}\n")


async def run_local(user_name: str, user_id: str):
    db              = Database(str(settings.DATABASE_PATH))
    memory          = Memory(db)
    profile_manager = UserProfileManager(db)
    emotion_engine  = EmotionEngine()
    decision        = DecisionEngine()
    session_manager = SessionManager(db)

    _print_header(user_name)

    # Saludo inicial
    greeting = session_manager.get_greeting(user_id)
    print(f"{SOFIA}{BOLD}Sofía:{RESET}{SOFIA} {greeting}{RESET}\n")

    while True:
        try:
            raw = input(f"{USER}{BOLD}{user_name}:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{INFO}Cerrando... hasta luego.{RESET}\n")
            break

        if not raw:
            continue

        # ── Comandos locales ──────────────────────────────────
        if raw.lower() in ("!salir", "!exit", "!quit"):
            print(f"\n{INFO}Cerrando... hasta luego.{RESET}\n")
            break

        if raw.lower() == "!reset":
            decision.aggression_count.pop(user_id, None)
            decision.recovery_needed.pop(user_id, None)
            decision.short_streak.pop(user_id, None)
            decision.secrets_revealed.pop(user_id, None)
            decision._secrets_date.pop(user_id, None)
            decision._topic_question_history.pop(user_id, None)
            decision._output_cooldowns.pop(user_id, None)
            decision._msg_counter.pop(user_id, None)
            print(f"{GREEN}  🔄 Contadores reseteados.{RESET}\n")
            continue

        if raw.lower() == "!estado":
            profile = await profile_manager.get_or_create_profile(user_id)
            e       = profile.emotional_state
            emo     = e.primary_emotion.value
            dmg     = profile.relationship_damage
            mood_r  = emotion_engine.get_mood_reason(user_id) or "sin razón"
            night   = emotion_engine.is_night_mode()
            agg     = decision.aggression_count.get(user_id, 0)
            rec     = decision.recovery_needed.get(user_id, 0)
            sem     = getattr(profile, "semantic_facts", {})

            print(f"\n{INFO}{'─'*48}")
            print(f"  Estado completo de Sofía")
            print(f"{'─'*48}")
            print(f"  Emoción:   {emo}")
            print(f"  Energía:   {e.energy:.1f} / 100")
            print(f"  Confianza: {e.trust:.1f} / 100")
            print(f"  Daño:      {dmg:.2f}")
            print(f"  Razón:     {mood_r}")
            print(f"  Noche:     {'sí' if night else 'no'}")
            print(f"  Agresiones:{agg}  Recovery:{rec}")
            print(f"  Frases guardadas: {len(profile.important_quotes)}")
            if sem:
                print(f"  Lo que sé de ti:")
                for k, v in list(sem.items())[:8]:
                    print(f"    {k}: {v}")
            print(f"{'─'*48}{RESET}\n")
            continue

        # ── Procesar mensaje normal ───────────────────────────
        profile   = await profile_manager.get_or_create_profile(user_id)
        modifiers = profile_manager.get_behavior_modifiers(profile)

        decision_result = await decision.decide_response(
            user_id=user_id,
            message=raw,
            emotion=profile.emotional_state,
            memory=memory,
            profile_modifiers=modifiers,
            display_name=user_name,
            emotion_engine=emotion_engine,
            profile_manager=profile_manager,
            profile=profile,
        )

        interaction       = decision_result["interaction"]
        repair_multiplier = decision.analyzer.get_repair_multiplier(raw)

        aggression_impact = None
        if decision_result["action"] in ("boundary", "silence", "limit"):
            agg_result = decision.aggression_detector.detect(
                raw, trust=profile.emotional_state.trust
            )
            if agg_result["detected"]:
                aggression_impact = agg_result["impact"]

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

        response = decision_result["response"]
        action   = decision_result["action"]

        print(f"\n{SOFIA}{BOLD}Sofía:{RESET}{SOFIA} {response}{RESET}")
        print(_estado_line(profile, action))
        print()


def main():
    parser = argparse.ArgumentParser(description="Prueba a Sofía en local sin Discord.")
    parser.add_argument("--user", default="tú",   help="Tu nombre de usuario")
    parser.add_argument("--id",   default="local_user", help="Tu user_id simulado")
    args = parser.parse_args()

    asyncio.run(run_local(user_name=args.user, user_id=args.id))


if __name__ == "__main__":
    main()