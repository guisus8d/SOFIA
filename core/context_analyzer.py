# core/context_analyzer.py
# ============================================================
# ContextAnalyzer — análisis del contexto conversacional y
# ajuste efectivo del estado emocional para selección de templates.
# Extraído de decision_engine.py en v0.13.0
# ============================================================


class ContextAnalyzer:

    def __init__(self, text_analyzer):
        self.analyzer = text_analyzer

    def analyze(self, current_message: str, current_sentiment: float,
                recent_interactions: list, current_keywords: list) -> dict:
        context = {
            "repetition_level": 0,
            "emotional_swing": False,
            "push_pull": False,
            "swing_direction": None,
        }
        if not recent_interactions:
            return context

        current_clean   = current_message.strip().lower()
        identical_count = sum(
            1 for inter in recent_interactions
            if inter.message.strip().lower() == current_clean
        )
        if identical_count >= 2:
            context["repetition_level"] = 2
        elif identical_count == 1:
            context["repetition_level"] = 1
        else:
            current_kw      = set(w for w in current_keywords if len(w) > 4)
            keyword_repeats = 0
            for inter in recent_interactions:
                prev_kw = set(w for w in self.analyzer.extract_keywords(inter.message) if len(w) > 4)
                if len(current_kw & prev_kw) >= 2:
                    keyword_repeats += 1
            if keyword_repeats >= 2:
                context["repetition_level"] = 1

        sentiments = [i.sentiment for i in recent_interactions if i.sentiment is not None]

        if sentiments:
            if max(sentiments) - min(sentiments) > 0.8:
                context["emotional_swing"] = True
                avg_past = sum(sentiments) / len(sentiments)
                context["swing_direction"] = "positive" if current_sentiment > avg_past else "negative"

        if len(recent_interactions) >= 2:
            all_sents = sentiments + [current_sentiment]
            signs     = [1 if s > 0.15 else (-1 if s < -0.15 else 0) for s in all_sents]
            non_zero  = [s for s in signs if s != 0]
            if len(non_zero) >= 3:
                alternating = all(non_zero[i] != non_zero[i + 1] for i in range(len(non_zero) - 1))
                if alternating:
                    context["push_pull"]       = True
                    context["emotional_swing"] = True

        if context["push_pull"]:
            context["repetition_level"] = 0

        return context

    @staticmethod
    def effective_emotion(emotion, agg_count: int, rec_needed: int, sentiment):
        """
        Devuelve un EmotionalState ajustado SOLO para selección de template.
        No modifica el estado real del perfil.

        CASO A — Conflicto/recovery activo: usar estado real.
        CASO B — Usuario negativo: no responder con alegría (cap a neutral).
        CASO C — Sin conflicto, mensaje neutro/positivo, energía baja: floor en 35.
        """
        from copy import copy
        from models.state import Emotion as _Emotion

        if agg_count > 0 or rec_needed > 0:
            return emotion

        if sentiment is not None and sentiment < -0.2:
            if emotion.primary_emotion == _Emotion.HAPPY:
                eff = copy(emotion)
                eff.primary_emotion = _Emotion.NEUTRAL
                return eff
            return emotion

        if sentiment is not None and sentiment >= -0.1 and emotion.energy < 35:
            eff = copy(emotion)
            eff.energy = 35.0
            if eff.energy > 65 and eff.trust > 60:
                eff.primary_emotion = _Emotion.HAPPY
            elif eff.trust < 25:
                eff.primary_emotion = _Emotion.ANGRY
            else:
                eff.primary_emotion = _Emotion.NEUTRAL
            return eff

        return emotion