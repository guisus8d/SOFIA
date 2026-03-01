# config/voice/__init__.py
# ============================================================
# Re-exports de todos los módulos de voz.
# Mantiene compatibilidad total con el import original:
#   from config.sofia_voice import X  →  sigue funcionando
# ============================================================

from config.voice._base import (
    _normalize,
    pick,
    trust_level,
)

from config.voice.identity import (
    SOFIA_INFO,
    RESPUESTAS_IDENTIDAD,
    detect_identity_question,
)

from config.voice.opinions import (
    OPINIONES,
    TOPIC_ALIASES,
    TopicLock,
    _topic_lock,
    get_opinion,
)

from config.voice.responses import (
    CONTEXTO,
    RESPUESTAS,
    MICRO_EXPRESIONES,
    micro_expresion,
    REPEAT_RESPONSES,
    CURIOSITY_QUESTIONS,
    MOMENTUM_DEPTH_PROMPTS,
)

from config.voice.escalation import (
    ESCALATION_RESPONSES,
    RECOVERY_RESPONSES,
    RESPUESTAS_NOCHE,
    NIGHT_RESPONSES,
    QUOTE_RECALL_PHRASES,
)

from config.voice.direct import (
    DIRECT_QUESTIONS,
    detect_direct_question,
)

from config.voice.initiative import (
    SOFIA_THOUGHTS,
    CUENTAME_TRIGGERS,
    get_sofia_thought,
    is_cuentame_trigger,
)

from config.voice.personality import (
    TIERNAS,
    MARCA_PERSONAL,
    MEXICANISMOS,
    saludo_ocasional,
    mexicanismo_aleatorio,
    DAILY_MOODS,
    get_sofia_daily_mood,
    sofia_mood_expression,
    SOFIA_SELF_SHARE,
    sofia_self_share,
    SOFIA_REACTIONS_WITH_SELF,
    sofia_reaction_with_self,
)

from config.voice.tone import (
    TONE_OPENERS,
    TONE_CLOSERS,
    micro_expresion_v2,
    apply_verbosity,
    initiative_allows_question,
    pick_by_tone,
    tone_closer,
)

__all__ = [
    # _base
    "_normalize", "pick", "trust_level",
    # identity
    "SOFIA_INFO", "RESPUESTAS_IDENTIDAD", "detect_identity_question",
    # opinions
    "OPINIONES", "TOPIC_ALIASES", "TopicLock", "_topic_lock", "get_opinion",
    # responses
    "CONTEXTO", "RESPUESTAS", "MICRO_EXPRESIONES", "micro_expresion",
    "REPEAT_RESPONSES", "CURIOSITY_QUESTIONS", "MOMENTUM_DEPTH_PROMPTS",
    # escalation
    "ESCALATION_RESPONSES", "RECOVERY_RESPONSES",
    "RESPUESTAS_NOCHE", "NIGHT_RESPONSES", "QUOTE_RECALL_PHRASES",
    # direct
    "DIRECT_QUESTIONS", "detect_direct_question",
    # initiative
    "SOFIA_THOUGHTS", "CUENTAME_TRIGGERS", "get_sofia_thought", "is_cuentame_trigger",
    # personality
    "TIERNAS", "MARCA_PERSONAL", "MEXICANISMOS", "saludo_ocasional",
    "mexicanismo_aleatorio", "DAILY_MOODS", "get_sofia_daily_mood",
    "sofia_mood_expression", "SOFIA_SELF_SHARE", "sofia_self_share",
    "SOFIA_REACTIONS_WITH_SELF", "sofia_reaction_with_self",
    # tone
    "TONE_OPENERS", "TONE_CLOSERS", "micro_expresion_v2", "apply_verbosity",
    "initiative_allows_question", "pick_by_tone", "tone_closer",
]