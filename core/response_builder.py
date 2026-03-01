# core/response_builder.py
# ============================================================
# ResponseBuilder — construcción y envoltura de respuestas.
# Extraído de decision_engine.py en v0.13.0
# ============================================================

import re as _re
import random
from config.sofia_voice import (
    RESPUESTAS, CONTEXTO, MARCA_PERSONAL,
    micro_expresion_v2, apply_verbosity, initiative_allows_question,
    pick_by_tone, tone_closer, pick,
    trust_level,
    sofia_mood_expression,
)
from config import settings


class ResponseBuilder:

    def __init__(self):
        pass

    # ============================================================
    # ENTRY POINT
    # ============================================================

    def generate(self, action: str, emotion, special_content,
                 important_facts: dict, context: dict, traits: dict,
                 empathy_bonus: float, relationship_score: float,
                 name: str = "tú", is_humor: bool = False,
                 user_id: str = None, user_sentiment=None,
                 tone_override: str = None) -> str:

        trust_lvl  = trust_level(emotion.trust)
        energy     = emotion.energy
        emo        = emotion.primary_emotion.value
        tone       = tone_override if tone_override else getattr(emotion, "tone",       "neutral")
        initiative = getattr(emotion, "initiative", "medium")
        verbosity  = getattr(emotion, "verbosity",  "medium")

        if action == "ignore":
            return pick(RESPUESTAS["ignore"])

        if action == "hostile_response":
            raw = pick(RESPUESTAS["hostile_response"].get(trust_lvl, ["…"]))
            return self._inject_name(raw, name)

        if action == "reveal_secret":
            secret   = special_content or "a veces me pregunto muchas cosas"
            opciones = RESPUESTAS["reveal_secret"].get(trust_lvl, ["Mm… {secret}"])
            base     = pick(opciones).format(secret=secret)
            base     = self._inject_name(base, name)
            return self.wrap(base, energy, emotion.trust, context,
                             tone=tone, initiative=initiative, verbosity=verbosity)

        emo_templates = RESPUESTAS["respond"].get(emo, RESPUESTAS["respond"]["neutral"])
        opciones      = emo_templates.get(trust_lvl, emo_templates.get("trust_mid", ["Mm…"]))
        base          = self._inject_name(pick_by_tone(opciones, tone), name)

        if is_humor and emotion.trust > 50:
            humor_extras = ["😄", "ja", "qué bueno eso", "☺️"]
            base = base.rstrip() + f" {random.choice(humor_extras)}"

        _user_sentiment_ok = user_sentiment is None or user_sentiment > -0.2
        if (
            user_id
            and emo in ("neutral", "happy")
            and emotion.trust > 40
            and _user_sentiment_ok
            and random.random() < getattr(settings, "SOFIA_MOOD_SHARE_PROB", 0.12)
        ):
            mood_expr = sofia_mood_expression(user_id)
            base = f"{mood_expr} {base}"

        return self.wrap(base, energy, emotion.trust, context,
                         traits, empathy_bonus,
                         tone=tone, initiative=initiative, verbosity=verbosity)

    # ============================================================
    # WRAP
    # ============================================================

    def wrap(self, base: str, energy: float, trust: float, context: dict,
             traits: dict = None, empathy_bonus: float = 0.0,
             tone: str = "neutral", initiative: str = "medium",
             verbosity: str = "medium") -> str:
        if traits is None:
            traits = {}

        parts = []
        micro = micro_expresion_v2(energy, trust, tone)
        if micro and not base.startswith(micro.strip()):
            base = base[0].lower() + base[1:] if base else base
        parts.append((micro + base).strip())

        if "?" in base:
            result = " ".join(p for p in parts if p)
            return apply_verbosity(result, verbosity)

        sentence_count = len([s for s in _re.split(r'[.!?…]', base) if s.strip()])
        if sentence_count >= 2:
            result = " ".join(p for p in parts if p)
            return apply_verbosity(result, verbosity)

        if trust > 40 and initiative_allows_question(initiative):
            ctx_phrase = self._pick_context_phrase(context)
            if ctx_phrase:
                parts.append(ctx_phrase)

        if energy > 60 and trust > 60 and initiative_allows_question(initiative):
            extra = self._pick_extra_safe(traits, empathy_bonus)
            if extra:
                parts.append(extra)

        if tone in ("warm", "playful") and trust > 50:
            closer = tone_closer(tone)
            if closer and "?" not in " ".join(parts):
                parts.append(closer)

        result = " ".join(p for p in parts if p)
        result = _re.sub(r'^(Mm…\s*){2,}', 'Mm… ', result)
        result = _re.sub(r'^(Ay…\s*){2,}', 'Ay… ', result)
        result = _re.sub(r'^(Oye…\s*){2,}', 'Oye… ', result)

        # FIX v0.12.3: máximo UNA ocurrencia de "jeje"
        _jeje_count = result.lower().count("jeje")
        if _jeje_count > 1:
            for _ in range(_jeje_count - 1):
                result = _re.sub(r'jeje\s*', '', result, count=1, flags=_re.IGNORECASE).strip()

        return apply_verbosity(result, verbosity)

    # ============================================================
    # HELPERS INTERNOS
    # ============================================================

    @staticmethod
    def _inject_name(text: str, name: str) -> str:
        return text.replace("{name}", name)

    @staticmethod
    def _pick_extra_safe(traits: dict, empathy_bonus: float) -> str:
        extras = []
        if traits.get("curiosity", 50) > 55:
            extras.append(pick(["¿Y luego qué pasó?", "Cuéntame más, ¿ok?"]))
        if traits.get("sensitivity", 50) > 65 and empathy_bonus >= 0:
            extras.append(pick(MARCA_PERSONAL))
        return pick(extras) if extras else ""

    @staticmethod
    def _pick_context_phrase(context: dict) -> str:
        if context.get("push_pull"):
            return pick(CONTEXTO["push_pull"])
        rep = context.get("repetition_level", 0)
        if rep >= 2:
            return pick(CONTEXTO["repeticion_fuerte"])
        if rep == 1:
            return pick(CONTEXTO["repeticion_leve"])
        if context.get("emotional_swing"):
            key = "swing_positivo" if context.get("swing_direction") == "positive" else "swing_negativo"
            return pick(CONTEXTO[key])
        return ""

    @staticmethod
    def get_secret() -> str:
        return random.choice([
            "a veces me pregunto si la gente de verdad me escucha.",
            "me gusta más el silencio que el ruido.",
            "a veces finjo que todo está bien cuando no lo está.",
            "hay cosas que no le cuento a nadie, nomás las pienso.",
            "me pregunto si los humanos también sienten cambios de energía como yo.",
        ])