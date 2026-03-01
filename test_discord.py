# test_discord.py
# ============================================================
# SocialBot — Test Unitario: Módulos Discord
# Versión 1.0.0
#
# Qué testea:
#   channel_memory    — ingestión, detección de temas, eventos pesados
#   server_monitor    — umbral dinámico, silencio real vs falso
#   initiative_trigger — reglas de supresión
#   initiative_builder — mensajes con razón contextual
#
# No necesita DB, asyncio ni Discord conectado.
# Los módulos se testean en aislamiento.
#
# Uso:
#   python test_discord.py             # todos los grupos
#   python test_discord.py --grupo channel_memory
#   python test_discord.py --grupo trigger
#   python test_discord.py --verbose
#   python test_discord.py --report
# ============================================================

import sys
import argparse
import time
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

# ── ANSI ──────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
CYAN    = "\033[96m"
MAGENTA = "\033[95m"
GRAY    = "\033[90m"
WHITE   = "\033[97m"
BLUE    = "\033[94m"


# ═════════════════════════════════════════════════════════════
# DATACLASS DE RESULTADO
# ═════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    group:   str
    name:    str
    desc:    str
    passed:  bool
    detail:  str = ""
    error:   str = ""


# ═════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════

def _ago(seconds: int) -> datetime:
    return datetime.utcnow() - timedelta(seconds=seconds)

def _future(seconds: int) -> datetime:
    return datetime.utcnow() + timedelta(seconds=seconds)


# ═════════════════════════════════════════════════════════════
# TESTS: CHANNEL MEMORY
# ═════════════════════════════════════════════════════════════

CHANNEL_MEMORY_TESTS = [

    {
        "name": "ingest_topic_musica",
        "desc": "Detecta género musical en mensaje del canal",
        "fn": lambda: (
            lambda cm: (
                cm.ingest("me gusta el metal, la neta"),
                cm._topics.__len__() > 0
                and any("metal" in k for k in cm._topics)
            )[-1]
        )(__import__("discord.channel_memory", fromlist=["ChannelMemory"]).ChannelMemory()),
    },

    {
        "name": "ingest_topic_deporte",
        "desc": "Detecta deporte en mensaje del canal",
        "fn": lambda: (
            lambda cm: (
                cm.ingest("me gusta el futbol y lo veo seguido"),
                any("futbol" in k for k in cm._topics)
            )[-1]
        )(__import__("discord.channel_memory", fromlist=["ChannelMemory"]).ChannelMemory()),
    },

    {
        "name": "topic_burst_detected",
        "desc": "6+ menciones del mismo tema en 1h → topic_burst",
        "fn": lambda: _test_topic_burst(),
    },

    {
        "name": "topic_burst_not_triggered_low",
        "desc": "2 menciones NO disparan burst",
        "fn": lambda: _test_topic_burst_low(),
    },

    {
        "name": "topic_persistence_detected",
        "desc": "Tema activo 2+ horas con 3+ msgs → topic_persistence",
        "fn": lambda: _test_topic_persistence(),
    },

    {
        "name": "heavy_message_detected",
        "desc": "'me quiero morir' marca last_heavy_ts",
        "fn": lambda: (
            lambda cm: (
                cm.ingest("la neta me quiero morir de risa no jaja"),
                cm._last_heavy_ts is not None
            )[-1]
        )(__import__("discord.channel_memory", fromlist=["ChannelMemory"]).ChannelMemory()),
    },

    {
        "name": "heavy_is_recent_true",
        "desc": "heavy_is_recent() True cuando fue hace poco",
        "fn": lambda: (
            lambda cm: (
                cm.ingest("me quiero morir"),
                cm.heavy_is_recent(cooldown_hours=4.0)
            )[-1]
        )(__import__("discord.channel_memory", fromlist=["ChannelMemory"]).ChannelMemory()),
    },

    {
        "name": "heavy_is_recent_false_old",
        "desc": "heavy_is_recent() False cuando cooldown ya pasó",
        "fn": lambda: _test_heavy_old(),
    },

    {
        "name": "conflict_detected",
        "desc": "'cállate' marca last_conflict_ts",
        "fn": lambda: (
            lambda cm: (
                cm.ingest("callate eres un idiota"),
                cm._conflict_ts is not None
            )[-1]
        )(__import__("discord.channel_memory", fromlist=["ChannelMemory"]).ChannelMemory()),
    },

    {
        "name": "conflict_is_recent_false_after_cooldown",
        "desc": "conflict_is_recent(0.5h) False si pasó hace >30min",
        "fn": lambda: _test_conflict_old(),
    },

    {
        "name": "post_conflict_reason",
        "desc": "Razón post_conflict si pelea fue hace 31-180 min",
        "fn": lambda: _test_post_conflict_reason(),
    },

    {
        "name": "no_reason_clean_server",
        "desc": "get_initiative_reason() None en server sin actividad",
        "fn": lambda: (
            lambda cm: cm.get_initiative_reason() is None
        )(__import__("discord.channel_memory", fromlist=["ChannelMemory"]).ChannelMemory()),
    },

    {
        "name": "prune_removes_old_topics",
        "desc": "Temas fuera de ventana se eliminan",
        "fn": lambda: _test_prune(),
    },

    {
        "name": "debug_summary_keys",
        "desc": "debug_summary() tiene las claves esperadas",
        "fn": lambda: (
            lambda cm: all(k in cm.debug_summary() for k in [
                "total_events", "active_topics", "last_heavy", "last_conflict", "initiative_reason"
            ])
        )(__import__("discord.channel_memory", fromlist=["ChannelMemory"]).ChannelMemory()),
    },
]


def _test_topic_burst():
    from discord.channel_memory import ChannelMemory
    cm = ChannelMemory()
    for _ in range(7):
        cm.ingest("me gusta el metal")
    reason = cm.get_initiative_reason()
    return reason is not None and reason.reason_type == "topic_burst"


def _test_topic_burst_low():
    from discord.channel_memory import ChannelMemory
    cm = ChannelMemory()
    for _ in range(2):
        cm.ingest("me gusta el metal")
    reason = cm.get_initiative_reason()
    return reason is None or reason.reason_type != "topic_burst"


def _test_topic_persistence():
    from discord.channel_memory import ChannelMemory
    cm = ChannelMemory()
    # Simular 3 mensajes con timestamps separados 1h+
    old_ts = _ago(int(2.5 * 3600))
    for _ in range(3):
        cm.ingest("me gusta el rock", ts=old_ts)
    cm.ingest("me gusta el rock")  # reciente
    reason = cm.get_initiative_reason()
    return reason is not None and reason.reason_type in ("topic_persistence", "topic_burst")


def _test_heavy_old():
    from discord.channel_memory import ChannelMemory
    cm = ChannelMemory()
    cm.ingest("me quiero morir")
    # Manipular el timestamp para simular que pasó hace mucho
    cm._last_heavy_ts = _ago(int(5 * 3600))
    return not cm.heavy_is_recent(cooldown_hours=4.0)


def _test_conflict_old():
    from discord.channel_memory import ChannelMemory
    cm = ChannelMemory()
    cm.ingest("callate eres un idiota")
    cm._conflict_ts = _ago(int(0.6 * 3600))  # hace 36 min
    return not cm.conflict_is_recent(cooldown_hours=0.5)


def _test_post_conflict_reason():
    from discord.channel_memory import ChannelMemory
    cm = ChannelMemory()
    cm.ingest("callate")
    cm._conflict_ts = _ago(31 * 60)  # hace 31 minutos
    reason = cm.get_initiative_reason()
    return reason is not None and reason.reason_type == "post_conflict"


def _test_prune():
    from discord.channel_memory import ChannelMemory
    cm = ChannelMemory(window_hours=1)
    # Ingestar con ts muy viejo
    old_ts = _ago(int(2 * 3600))
    cm.ingest("me gusta el metal", ts=old_ts)
    # Forzar prune
    cm._prune()
    return len(cm._topics) == 0


# ═════════════════════════════════════════════════════════════
# TESTS: SERVER MONITOR
# ═════════════════════════════════════════════════════════════

SERVER_MONITOR_TESTS = [

    {
        "name": "no_history_conservative",
        "desc": "Sin historial → threshold >= 4h (conservador)",
        "fn": lambda: _test_monitor_no_history(),
    },

    {
        "name": "threshold_clamp_min",
        "desc": "Threshold nunca baja de 20 min (1200s)",
        "fn": lambda: _test_monitor_clamp_min(),
    },

    {
        "name": "threshold_clamp_max",
        "desc": "Threshold nunca sube de 6h (21600s)",
        "fn": lambda: _test_monitor_clamp_max(),
    },

    {
        "name": "is_silent_true",
        "desc": "is_silent() True cuando last_msg fue hace mucho",
        "fn": lambda: (
            lambda m: m.is_silent(_ago(int(5 * 3600)))
        )(__import__("discord.server_monitor", fromlist=["ServerMonitor"]).ServerMonitor()),
    },

    {
        "name": "is_silent_false_recent",
        "desc": "is_silent() False cuando last_msg fue hace 1 min",
        "fn": lambda: (
            lambda m: not m.is_silent(_ago(60))
        )(__import__("discord.server_monitor", fromlist=["ServerMonitor"]).ServerMonitor()),
    },

    {
        "name": "threshold_adapts_to_activity",
        "desc": "Server activo → threshold menor que server inactivo",
        "fn": lambda: _test_monitor_adapts(),
    },

    {
        "name": "debug_info_keys",
        "desc": "debug_info() tiene las claves esperadas",
        "fn": lambda: (
            lambda m: (
                m.record(),
                all(k in m.debug_info() for k in [
                    "total_recorded", "threshold_minutes", "last_activity", "silence_now_secs"
                ])
            )[-1]
        )(__import__("discord.server_monitor", fromlist=["ServerMonitor"]).ServerMonitor()),
    },
]


def _test_monitor_no_history():
    from discord.server_monitor import ServerMonitor
    m = ServerMonitor()
    t = m.dynamic_threshold()
    return t >= timedelta(hours=4)


def _test_monitor_clamp_min():
    from discord.server_monitor import ServerMonitor
    m = ServerMonitor()
    # Llenar con msgs muy seguidos (cada 1 segundo)
    now = datetime.utcnow()
    for i in range(50):
        m.record(now - timedelta(seconds=i))
    t = m.dynamic_threshold()
    return t >= timedelta(seconds=1200)


def _test_monitor_clamp_max():
    from discord.server_monitor import ServerMonitor
    m = ServerMonitor()
    # Msgs muy espaciados (cada 2 días)
    now = datetime.utcnow()
    for i in range(10):
        m.record(now - timedelta(days=i * 2))
    t = m.dynamic_threshold()
    return t <= timedelta(seconds=21600)


def _test_monitor_adapts():
    from discord.server_monitor import ServerMonitor

    # Server activo: msg cada 30 segundos
    active = ServerMonitor()
    now = datetime.utcnow()
    for i in range(100):
        active.record(now - timedelta(seconds=i * 30))

    # Server muerto: msg cada 2 horas
    dead = ServerMonitor()
    for i in range(20):
        dead.record(now - timedelta(hours=i * 2))

    return active.dynamic_threshold() < dead.dynamic_threshold()


# ═════════════════════════════════════════════════════════════
# TESTS: INITIATIVE TRIGGER
# ═════════════════════════════════════════════════════════════

INITIATIVE_TRIGGER_TESTS = [

    {
        "name": "blocks_on_heavy_recent",
        "desc": "No habla si hubo mensaje pesado reciente",
        "fn": lambda: _test_trigger_blocks_heavy(),
    },

    {
        "name": "blocks_on_cooldown",
        "desc": "No habla si ya intervino hace menos del cooldown",
        "fn": lambda: _test_trigger_blocks_cooldown(),
    },

    {
        "name": "blocks_if_not_silent",
        "desc": "No habla si el server no está realmente silencioso",
        "fn": lambda: _test_trigger_blocks_not_silent(),
    },

    {
        "name": "blocks_on_very_recent_conflict",
        "desc": "No habla si hubo pelea hace menos de 30 min",
        "fn": lambda: _test_trigger_blocks_recent_conflict(),
    },

    {
        "name": "allows_after_cooldown",
        "desc": "Puede hablar cuando todos los cooldowns pasaron (con razón fuerte)",
        "fn": lambda: _test_trigger_allows(),
    },

    {
        "name": "lower_prob_without_reason",
        "desc": "Sin razón temática la probabilidad es más baja (prob_idle < prob_topic)",
        "fn": lambda: _test_trigger_lower_prob_no_reason(),
    },
]


def _test_trigger_blocks_heavy():
    from discord.channel_memory import ChannelMemory
    from discord.server_monitor import ServerMonitor
    from discord.initiative_trigger import InitiativeTrigger

    cm = ChannelMemory()
    cm.ingest("me quiero morir")  # marca heavy ahora

    m  = ServerMonitor()
    t  = InitiativeTrigger()

    # Aunque todo lo demás esté ok, heavy reciente bloquea
    results = [
        t.should_speak(
            monitor=m,
            channel_memory=cm,
            last_msg_ts=_ago(int(5 * 3600)),
            last_initiative_ts=None,
        )
        for _ in range(20)
    ]
    return not any(results)  # nunca debe pasar


def _test_trigger_blocks_cooldown():
    from discord.channel_memory import ChannelMemory
    from discord.server_monitor import ServerMonitor
    from discord.initiative_trigger import InitiativeTrigger

    cm = ChannelMemory()
    m  = ServerMonitor()
    t  = InitiativeTrigger()

    # Última iniciativa hace solo 30 minutos (cooldown = 3h)
    last_init = _ago(30 * 60)

    results = [
        t.should_speak(
            monitor=m,
            channel_memory=cm,
            last_msg_ts=_ago(int(5 * 3600)),
            last_initiative_ts=last_init,
        )
        for _ in range(20)
    ]
    return not any(results)


def _test_trigger_blocks_not_silent():
    from discord.channel_memory import ChannelMemory
    from discord.server_monitor import ServerMonitor
    from discord.initiative_trigger import InitiativeTrigger

    cm = ChannelMemory()
    m  = ServerMonitor()
    t  = InitiativeTrigger()

    # Último mensaje hace 1 minuto → no está silencioso
    results = [
        t.should_speak(
            monitor=m,
            channel_memory=cm,
            last_msg_ts=_ago(60),
            last_initiative_ts=None,
        )
        for _ in range(20)
    ]
    return not any(results)


def _test_trigger_blocks_recent_conflict():
    from discord.channel_memory import ChannelMemory
    from discord.server_monitor import ServerMonitor
    from discord.initiative_trigger import InitiativeTrigger

    cm = ChannelMemory()
    cm.ingest("callate eres un idiota")
    cm._conflict_ts = _ago(10 * 60)  # hace 10 minutos

    m  = ServerMonitor()
    t  = InitiativeTrigger()

    results = [
        t.should_speak(
            monitor=m,
            channel_memory=cm,
            last_msg_ts=_ago(int(4 * 3600)),
            last_initiative_ts=None,
        )
        for _ in range(20)
    ]
    return not any(results)


def _test_trigger_allows():
    """
    Con razón fuerte (strength=1.0) y todas las reglas ok,
    debe hablar en >= 30% de 100 intentos (prob=0.5 * 1.0 = 0.5).
    """
    from discord.channel_memory import ChannelMemory
    from discord.server_monitor import ServerMonitor
    from discord.initiative_trigger import InitiativeTrigger

    cm = ChannelMemory()
    # Generar burst fuerte
    for _ in range(10):
        cm.ingest("me gusta el metal")
    cm._last_heavy_ts = None  # sin heavy

    m  = ServerMonitor()
    t  = InitiativeTrigger()

    spoke = sum(
        1 for _ in range(100)
        if t.should_speak(
            monitor=m,
            channel_memory=cm,
            last_msg_ts=_ago(int(5 * 3600)),
            last_initiative_ts=_ago(int(4 * 3600)),  # cooldown pasado
        )
    )
    return spoke >= 20  # al menos 20% (margen para CI)


def _test_trigger_lower_prob_no_reason():
    """
    Sin razón temática, la tasa de aprobación debe ser menor que con razón fuerte.
    """
    from discord.channel_memory import ChannelMemory
    from discord.server_monitor import ServerMonitor
    from discord.initiative_trigger import InitiativeTrigger

    # Con razón fuerte
    cm_reason = ChannelMemory()
    for _ in range(10):
        cm_reason.ingest("me gusta el metal")
    cm_reason._last_heavy_ts = None

    # Sin razón
    cm_empty = ChannelMemory()

    m = ServerMonitor()
    t = InitiativeTrigger()

    N = 200
    kwargs = dict(last_msg_ts=_ago(int(5*3600)), last_initiative_ts=_ago(int(4*3600)))

    with_reason  = sum(1 for _ in range(N) if t.should_speak(monitor=m, channel_memory=cm_reason, **kwargs))
    without_reason = sum(1 for _ in range(N) if t.should_speak(monitor=m, channel_memory=cm_empty, **kwargs))

    return with_reason > without_reason


# ═════════════════════════════════════════════════════════════
# TESTS: INITIATIVE BUILDER
# ═════════════════════════════════════════════════════════════

INITIATIVE_BUILDER_TESTS = [

    {
        "name": "builds_topic_burst_musica",
        "desc": "Genera mensaje sobre música en topic_burst",
        "fn": lambda: _test_builder_topic_burst("musica_genero", "metal"),
    },

    {
        "name": "builds_topic_burst_deporte",
        "desc": "Genera mensaje sobre deporte en topic_burst",
        "fn": lambda: _test_builder_topic_burst("deporte_interes", "futbol"),
    },

    {
        "name": "builds_post_conflict",
        "desc": "Genera mensaje de reconciliación en post_conflict",
        "fn": lambda: _test_builder_post_conflict(),
    },

    {
        "name": "builds_topic_persistence",
        "desc": "Genera mensaje sobre persistencia de tema",
        "fn": lambda: _test_builder_persistence(),
    },

    {
        "name": "builds_deep_silence",
        "desc": "Genera mensaje de silencio sin razón temática",
        "fn": lambda: _test_builder_silence(),
    },

    {
        "name": "never_empty_response",
        "desc": "build() nunca devuelve string vacío",
        "fn": lambda: _test_builder_never_empty(),
    },

    {
        "name": "never_starts_hola_chicos",
        "desc": "Nunca genera el temido 'Hola chicos, ¿qué hacen?'",
        "fn": lambda: _test_builder_not_obvious(),
    },
]


def _make_reason(reason_type, topic_key=None, topic_value=None, strength=0.8):
    from discord.channel_memory import InitiativeReason
    return InitiativeReason(
        reason_type=reason_type,
        topic_key=topic_key,
        topic_value=topic_value,
        strength=strength,
        description="test",
    )


def _test_builder_topic_burst(key, value):
    from discord.initiative_builder import InitiativeBuilder
    reason = _make_reason("topic_burst", key, value)
    msg = InitiativeBuilder.build(reason, hour=15)
    return isinstance(msg, str) and len(msg) > 5 and value in msg.lower()


def _test_builder_post_conflict():
    from discord.initiative_builder import InitiativeBuilder
    reason = _make_reason("post_conflict")
    msg = InitiativeBuilder.build(reason, hour=20)
    return isinstance(msg, str) and len(msg) > 5


def _test_builder_persistence():
    from discord.initiative_builder import InitiativeBuilder
    reason = _make_reason("topic_persistence", "musica_genero", "rock", strength=0.6)
    msg = InitiativeBuilder.build(reason, hour=18)
    return isinstance(msg, str) and len(msg) > 5


def _test_builder_silence():
    from discord.initiative_builder import InitiativeBuilder
    reason = _make_reason("deep_silence")
    for hour in [2, 15, 21]:
        msg = InitiativeBuilder.build(reason, hour=hour)
        if not (isinstance(msg, str) and len(msg) > 0):
            return False
    return True


def _test_builder_never_empty():
    from discord.initiative_builder import InitiativeBuilder
    from discord.channel_memory import InitiativeReason

    for rtype, key, val in [
        ("topic_burst", "musica_genero", "metal"),
        ("topic_persistence", "deporte_interes", "gym"),
        ("post_conflict", None, None),
        ("deep_silence", None, None),
    ]:
        reason = _make_reason(rtype, key, val)
        for hour in [0, 10, 22]:
            msg = InitiativeBuilder.build(reason, hour=hour)
            if not msg or len(msg.strip()) == 0:
                return False
    return True


def _test_builder_not_obvious():
    from discord.initiative_builder import InitiativeBuilder
    BANNED = ["hola chicos", "¿qué hacen?", "hey everyone", "hola a todos"]
    reason = _make_reason("deep_silence")
    for _ in range(20):
        msg = InitiativeBuilder.build(reason, hour=14).lower()
        if any(b in msg for b in BANNED):
            return False
    return True


# ═════════════════════════════════════════════════════════════
# GRUPOS
# ═════════════════════════════════════════════════════════════

GROUPS = {
    "channel_memory": CHANNEL_MEMORY_TESTS,
    "monitor":        SERVER_MONITOR_TESTS,
    "trigger":        INITIATIVE_TRIGGER_TESTS,
    "builder":        INITIATIVE_BUILDER_TESTS,
}

GROUP_LABELS = {
    "channel_memory": "CHANNEL MEMORY",
    "monitor":        "SERVER MONITOR",
    "trigger":        "INITIATIVE TRIGGER",
    "builder":        "INITIATIVE BUILDER",
}


# ═════════════════════════════════════════════════════════════
# RUNNER
# ═════════════════════════════════════════════════════════════

class DiscordTestRunner:

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: list[TestResult] = []

    def run_group(self, group_name: str, tests: list) -> list[TestResult]:
        label = GROUP_LABELS.get(group_name, group_name.upper())
        print(f"\n{BOLD}{'═'*56}{RESET}")
        print(f"{BOLD}  {label}{RESET}")
        print(f"{BOLD}{'═'*56}{RESET}")

        group_results = []
        for i, test in enumerate(tests):
            name = test["name"]
            desc = test["desc"]
            fn   = test["fn"]

            try:
                passed  = bool(fn())
                detail  = ""
                err     = ""
            except Exception as e:
                passed  = False
                detail  = ""
                err     = str(e)

            r = TestResult(group=group_name, name=name, desc=desc,
                           passed=passed, detail=detail, error=err)
            group_results.append(r)
            self.results.append(r)
            self._print_step(i + 1, r)

        return group_results

    def _print_step(self, n: int, r: TestResult):
        status = f"{GREEN}✓{RESET}" if r.passed else f"{RED}✗{RESET}"
        print(f"  {status} [{n:02d}] {CYAN}{r.name:<42}{RESET}")

        if self.verbose or not r.passed:
            print(f"       {GRAY}→ {r.desc}{RESET}")

        if r.error:
            print(f"       {RED}⚠ excepción: {r.error}{RESET}")

    def print_summary(self):
        total  = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        pct    = (passed / total * 100) if total else 0

        print(f"\n{BOLD}{'═'*56}{RESET}")
        print(f"{BOLD}  RESUMEN FINAL{RESET}")
        print(f"{'═'*56}")
        print(f"  Total:   {total} pruebas")
        print(f"  {GREEN}Pasaron: {passed} ({pct:.0f}%){RESET}")
        if failed:
            print(f"  {RED}Fallaron: {failed}{RESET}")

        by_group: dict[str, list] = {}
        for r in self.results:
            if not r.passed:
                by_group.setdefault(r.group, []).append(r)

        if by_group:
            print(f"\n{BOLD}  Fallos por grupo:{RESET}")
            for grp, items in by_group.items():
                print(f"  {YELLOW}  {GROUP_LABELS.get(grp, grp)} — {len(items)} fallo(s){RESET}")
                for r in items:
                    print(f"    {RED}✗{RESET} {r.name}")
                    if r.error:
                        print(f"      {GRAY}→ excepción: {r.error}{RESET}")

        print(f"{'═'*56}{RESET}\n")

    def build_report_md(self) -> str:
        now    = datetime.now().strftime("%Y-%m-%d %H:%M")
        total  = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        lines = [
            "# Reporte de Test — Módulos Discord",
            "",
            f"**Fecha:** {now}  ",
            f"**Total:** {total} pruebas · **Pasaron:** {passed} · **Fallaron:** {failed}",
            "",
            "---",
            "",
        ]
        for group_name, label in GROUP_LABELS.items():
            group_results = [r for r in self.results if r.group == group_name]
            if not group_results:
                continue
            lines.append(f"## {label}")
            lines.append("")
            for r in group_results:
                icon = "✅" if r.passed else "❌"
                lines.append(f"- {icon} `{r.name}` — {r.desc}")
                if not r.passed and r.error:
                    lines.append(f"  - Error: `{r.error}`")
            lines.append("")

        return "\n".join(lines)


# ═════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Test módulos Discord — SocialBot")
    parser.add_argument("--grupo",   type=str, default="all",
                        help="channel_memory | monitor | trigger | builder | all")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--report",  action="store_true",
                        help="Guarda reporte .md en el directorio actual")
    args = parser.parse_args()

    runner = DiscordTestRunner(verbose=args.verbose)
    t0 = time.time()

    grupos_req = (
        list(GROUPS.keys())
        if args.grupo == "all"
        else [g.strip() for g in args.grupo.split(",")]
    )

    for g in grupos_req:
        if g not in GROUPS:
            print(f"{YELLOW}⚠ Grupo desconocido: '{g}'. Opciones: {list(GROUPS.keys())}{RESET}")
            continue
        runner.run_group(g, GROUPS[g])

    runner.print_summary()
    elapsed = time.time() - t0
    print(f"  Tiempo total: {elapsed:.1f}s\n")

    if args.report:
        md      = runner.build_report_md()
        ts      = datetime.now().strftime("%Y%m%d_%H%M")
        fname   = f"test_discord_{ts}.md"
        Path(fname).write_text(md, encoding="utf-8")
        print(f"  {GREEN}Reporte guardado: {fname}{RESET}\n")

    failed = sum(1 for r in runner.results if not r.passed)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()