# discord/initiative_builder.py
# ============================================================
# InitiativeBuilder — construye el mensaje que Sofía envía
# cuando decide intervenir por iniciativa propia.
#
# Regla de oro: Sofía siempre habla DESDE la razón contextual.
# Nunca "hola chicos, ¿qué hacen?".
# ============================================================

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord.channel_memory import InitiativeReason


class InitiativeBuilder:

    @staticmethod
    def build(reason: "InitiativeReason", hour: int) -> str:
        """
        Construye el mensaje según el tipo de razón.
        """
        builders = {
            "post_conflict":      InitiativeBuilder._post_conflict,
            "topic_burst":        InitiativeBuilder._topic_burst,
            "topic_persistence":  InitiativeBuilder._topic_persistence,
            "deep_silence":       InitiativeBuilder._deep_silence,
        }
        fn = builders.get(reason.reason_type, InitiativeBuilder._deep_silence)
        return fn(reason, hour)

    # ── constructores por tipo ────────────────────────────────

    @staticmethod
    def _post_conflict(reason: "InitiativeReason", hour: int) -> str:
        opts = [
            "Oigan… ¿ya están mejor? El server se sintió raro hace rato.",
            "No sé qué pasó, pero espero que estén bien.",
            "Las discusiones pasan. ¿Ya se calmaron las cosas?",
            "Siguen ahí, ¿verdad? Solo quería saber.",
        ]
        return random.choice(opts)

    @staticmethod
    def _topic_burst(reason: "InitiativeReason", hour: int) -> str:
        val = reason.topic_value or "eso"
        templates_by_key = {
            "musica_genero": [
                f"Oigan… llevan rato hablando de {val}. ¿Qué están escuchando exactamente?",
                f"Tanto {val}... ¿alguna recomendación? Me quedo con curiosidad.",
                f"El {val} no para hoy aquí jeje. ¿Qué álbum?",
            ],
            "deporte_interes": [
                f"Mucho {val} hoy. ¿Pasó algo o solo están de buen humor deportivo?",
                f"No paro de leer {val} en el chat. ¿Están viendo algo?",
                f"Tanto {val}... ¿hay partido o solo se emocionaron solos jeje?",
            ],
            "hobby": [
                f"Harto {val} hoy. ¿Están trabajando en algo o solo hablando?",
                f"El tema de {val} no para. ¿Qué están haciendo exactamente?",
                f"Me llama la atención tanto {val} hoy. ¿Qué pasó?",
            ],
            "comida_favorita": [
                f"Oigan… tanto {val} y yo aquí con hambre vicario.",
                f"El {val} no para en el chat jeje. ¿Se fueron a comer o qué?",
                f"Tanta mención de {val}... ¿están comiendo o solo con antojos?",
            ],
        }
        key = reason.topic_key or ""
        opts = templates_by_key.get(key, [
            f"Llevan rato con {val}. ¿Qué onda con eso?",
            f"No para el tema de {val} hoy aquí.",
        ])
        return random.choice(opts)

    @staticmethod
    def _topic_persistence(reason: "InitiativeReason", hour: int) -> str:
        val = reason.topic_value or "ese tema"
        hours = round(reason.strength * 6, 1)  # aproximar span
        opts = [
            f"Curioso… llevan horas hablando de {val} y no paran.",
            f"El {val} resistió toda la tarde aquí. No es para menos jeje.",
            f"Siempre se vuelve a {val} en este server. ¿Por qué será?",
            f"Horas de {val}. Eso dice algo de ustedes.",
        ]
        return random.choice(opts)

    @staticmethod
    def _deep_silence(reason: "InitiativeReason", hour: int) -> str:
        # Solo si no hay razón temática, usa observación o pensamiento
        if 0 <= hour < 7:
            opts = [
                "Siempre se quedan callados después de las 11. Qué curioso.",
                "Hora rara. Pero aquí sigo.",
                "El silencio de madrugada tiene otro peso.",
            ]
        elif 14 <= hour < 17:
            opts = [
                "Las tardes aquí son raras. Todo el mundo y luego nadie.",
                "Hora de la siesta del server, veo jeje.",
                "¿Están o no están?",
            ]
        else:
            opts = [
                "Qué quieto está esto.",
                "El silencio tiene su propio ruido aquí jeje.",
                "Siguen ahí, ¿no?",
            ]
        # Como fallback también puede usar un pensamiento propio
        if random.random() < 0.3:
            try:
                from config.sofia_voice import get_sofia_thought
                return get_sofia_thought()
            except Exception:
                pass
        return random.choice(opts)