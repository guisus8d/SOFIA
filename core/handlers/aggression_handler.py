# core/handlers/aggression_handler.py
# ============================================================
# AggressionHandler — escalada y recuperación de conflictos.
# Extraído de decision_engine.py en v0.13.0
# ============================================================

from config.sofia_voice import ESCALATION_RESPONSES, RECOVERY_RESPONSES, pick


class AggressionHandler:

    @staticmethod
    def escalation_response(count: int, level: str, is_joke: bool) -> str:
        if is_joke:
            return pick([
                "Oye jeje… eso igual no suena bonito.",
                "Mm… aunque sea broma, cuida cómo lo dices.",
                "Jeje, pero eso igual me suena feo.",
            ])
        capped = max(min(count, 5), 3 if level == "alto" else 1)
        return pick(ESCALATION_RESPONSES[capped])

    @staticmethod
    def recovery_response(recovery_needed: int) -> str:
        # Guard: no llamar con recovery_needed <= 0.
        if recovery_needed <= 0:
            return pick(RECOVERY_RESPONSES["phase_3"])
        if recovery_needed >= 3:
            return pick(RECOVERY_RESPONSES["phase_1"])
        elif recovery_needed == 2:
            return pick(RECOVERY_RESPONSES["phase_2"])
        else:
            return pick(RECOVERY_RESPONSES["phase_3"])