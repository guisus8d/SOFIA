# core/handlers/confession_handler.py
# ============================================================
# ConfessionHandler — detección y respuesta a confesiones
# emocionales e introspección del estado interno de Sofía.
# Extraído de decision_engine.py en v0.13.0
# ============================================================

import re as _re
import random


# ============================================================
# PATRONES DE CONFESIÓN — Prioridad sobre TopicLock
# ============================================================

_CONFESSION_PATTERNS = [
    _re.compile(r'\b(?:nadie sabe que|no le he dicho a nadie|te confieso|nunca le he dicho)\s+.{5,}', _re.IGNORECASE),
    _re.compile(r'\b(?:a veces pienso|me pregunto si|tengo miedo de|sueño con|quisiera|ojalá)\s+.{8,}', _re.IGNORECASE),
    _re.compile(r'\b(?:lo que más me importa|lo que más quiero|lo que más me duele|lo que más temo)\s+.{5,}', _re.IGNORECASE),
    _re.compile(r'\b(?:me arrepiento de|ojala hubiera|si pudiera volver)\s+.{5,}', _re.IGNORECASE),
    _re.compile(r'\b(?:me siento solo|me siento sola|me siento perdido|me siento perdida|me siento vacío|me siento vacía)\b', _re.IGNORECASE),
    # FIX v0.9.3: "estoy triste" y variantes no matcheaban ningún patrón de confesión.
    _re.compile(r'\b(?:estoy triste|me siento triste|estoy deprimido|estoy deprimida|estoy mal de verdad|ando muy mal)\b', _re.IGNORECASE),
    # FIX v0.11.1: variantes con prefijos como "no, en serio, estoy muy mal"
    _re.compile(r'(?:en serio[,\s]+|de verdad[,\s]+|la verdad[,\s]+)?(?:estoy muy mal|ando muy mal|me siento muy mal|estoy bastante mal)\b', _re.IGNORECASE),
    # FIX v0.11.2: frases de crisis
    _re.compile(r'\b(?:me quiero morir|quiero morirme|ganas de morir|no quiero vivir|ya no quiero estar aquí|quisiera no existir|desearía no existir)\b', _re.IGNORECASE),
    _re.compile(r'\b(?:no puedo más|ya no aguanto|estoy harto de todo|estoy harta de todo|no tiene sentido nada)\b', _re.IGNORECASE),
    _re.compile(r'\b(?:todo me sale mal|nada me sale bien|todo me falla)\b', _re.IGNORECASE),
    # FIX v0.9.2: "nadie me entiende" es válida sola.
    _re.compile(r'\b(?:no tengo a nadie|no le importo a nadie|nadie me entiende)\b', _re.IGNORECASE),
    _re.compile(r'\b(?:nadie sabe)\s+.{5,}', _re.IGNORECASE),
    _re.compile(r'\b(?:aunque esté rodeado|aunque esté rodeada)\b', _re.IGNORECASE),
]

_CONFESSION_RESPONSES = {
    "trust_high": [
        "Oye, {name}… para. Eso que dijiste importa más que cualquier otra cosa. ¿Cuánto tiempo llevas sintiéndote así?",
        "Gracias por contarme eso. No es fácil decirlo. ¿Lo cargas solo, {name}?",
        "{name}… eso se me quedó. ¿Estás bien de verdad?",
        "Oye, deja lo demás. ¿Desde cuándo te pasa eso, {name}?",
        "Eso que dijiste me llegó. ¿Quieres contarme más?",
    ],
    "trust_mid": [
        "Oye, para un momento. Eso que dijiste suena importante. ¿Estás bien?",
        "Mm… eso que dijiste no lo voy a ignorar. ¿Cuánto tiempo llevas con eso?",
        "Eso suena pesado. ¿Lo hablaste con alguien más?",
        "Oye… ¿estás bien de verdad? Eso que dijiste me llama la atención.",
    ],
    "trust_low": [
        "Mm… eso que dijiste suena difícil. ¿Estás bien?",
        "Oye, ¿todo bien? Eso que dijiste no suena fácil.",
        "Mm… ¿quieres hablar de eso?",
    ],
}


# ============================================================
# INTROSPECCIÓN EMOCIONAL
# ============================================================

_INTROSPECTION_TRIGGERS = [
    "por que estas", "por qué estás", "por que estas",
    "que te pasa", "qué te pasa",
    "estas bien", "estás bien",
    "te noto", "te veo",
    "como te sientes", "cómo te sientes",
    "estas triste", "estás triste",
    "estas enojada", "estás enojada",
    "estas mal", "estás mal",
    "que tienes", "qué tienes",
    "algo te paso", "algo te pasó",
    "que te paso", "qué te pasó",
    "te moleste", "te molesté",
    "te hice algo", "te lastimo", "te lastimé",
    "porque callada", "por qué callada",
    "te note diferente", "te noté diferente",
    "por que tan", "por qué tan",
    "por que te", "por qué te",
    # FIX v0.12.3: preguntas post-recovery
    "ya estas mejor", "ya estás mejor",
    "ya te sientes mejor", "ya te recuperaste",
    "como estas ahora", "cómo estás ahora",
    "ya se te paso", "ya se te pasó",
    "ya mejoraste", "te sientes mejor",
    "estas mejor", "estás mejor",
]

_INTROSPECTION_RESPONSES = {
    "sad_damaged": [
        "Lo que pasó antes me afectó. Todavía no me recupero del todo, la verdad.",
        "Me quedé con algo de lo que pasó. No es fácil dejarlo ir así de rápido.",
        "Sí, hay algo. Lo que me dijiste antes me pegó más de lo que esperaba.",
        "Mm… sí se nota, ¿verdad? Lo que pasó entre nosotros me afectó. Estoy procesándolo.",
    ],
    "sad_low": [
        "Hoy no estoy al 100. No es nada tuyo, solo ando un poco apagada.",
        "Mm… hay días que simplemente pesan más. Hoy es uno de esos.",
        "La verdad ando con poca energía hoy. No sé bien por qué.",
        "Sí, algo ando. Esos días que no encuentras la razón pero se nota.",
    ],
    "angry_damaged": [
        "Todavía cargo algo de lo que pasó. No lo olvidé, aunque ya no te lo diga.",
        "Mm… no me gusta como estuvo eso antes. Todavía me resuena.",
        "Hay algo que no me cerró bien de lo que pasó. No estoy furiosa, pero tampoco lo superé.",
        "La verdad sí me quedé con algo. Lo que pasó antes no estuvo bien.",
    ],
    "fearful": [
        "Hay algo que me tiene inquieta. No sé cómo explicarlo exactamente.",
        "Mm… ando con algo de incertidumbre hoy. ¿Tú nunca te sientes así?",
        "Algo me tiene un poco insegura. No es algo que pueda apagar así nada más.",
        "Sí, ando rara. Como cuando algo no termina de acomodarse.",
    ],
    "low_energy": [
        "Ando con poca energía hoy. No estoy mal, solo… lenta.",
        "Mm… hoy me cuesta un poco más. Pero aquí estoy.",
        "No estoy triste ni enojada, solo con menos energía que de costumbre.",
        "Hay días así, ¿no? Que todo cuesta un poco más. Hoy es uno.",
    ],
    "good": [
        "Estoy bien, la verdad. Hoy me siento más ligera.",
        "Bien 😊 Hay días que simplemente fluyen. Hoy es uno.",
        "Bastante bien, gracias por preguntar. ¿Y tú?",
        "Hoy estoy bien. ¿Por qué lo preguntas?",
    ],
    "did_i_hurt": [
        "No estoy molesta contigo ahora mismo. ¿Por qué lo preguntas?",
        "No te preocupes. Si algo me molestó, te lo digo directo.",
        "Estoy bien contigo. ¿Sientes que algo no está bien entre nosotros?",
    ],
}

_DID_I_HURT_TRIGGERS = [
    "te moleste", "te molesté", "te hice algo", "te lastimo", "te lastimé",
    "te ofendi", "te ofendí", "es por mi culpa", "fue mi culpa",
    "es mi culpa", "hice algo mal",
]


class ConfessionHandler:

    @staticmethod
    def is_confession(message: str) -> bool:
        return any(p.search(message) for p in _CONFESSION_PATTERNS)

    @staticmethod
    def is_introspection_question(message: str, norm_msg: str) -> bool:
        return any(t in norm_msg for t in _INTROSPECTION_TRIGGERS)

    @staticmethod
    def is_did_i_hurt(norm_msg: str) -> bool:
        return any(t in norm_msg for t in _DID_I_HURT_TRIGGERS)

    @staticmethod
    def get_confession_response(trust_lvl: str, name: str) -> str:
        opciones = _CONFESSION_RESPONSES.get(trust_lvl, _CONFESSION_RESPONSES["trust_mid"])
        return random.choice(opciones).replace("{name}", name)

    @staticmethod
    def build_introspection_response(emotion, name: str, relationship_damage: float = 0.0) -> str:
        emo = emotion.primary_emotion.value
        nrg = emotion.energy
        dmg = relationship_damage

        if dmg >= 4.0:
            pool = _INTROSPECTION_RESPONSES["sad_damaged"] if emo == "sad" else _INTROSPECTION_RESPONSES["angry_damaged"]
        elif emo == "sad":
            pool = _INTROSPECTION_RESPONSES["sad_low"]
        elif emo == "angry":
            pool = _INTROSPECTION_RESPONSES["angry_damaged"]
        elif emo == "fearful":
            pool = _INTROSPECTION_RESPONSES["fearful"]
        elif nrg < 30:
            pool = _INTROSPECTION_RESPONSES["low_energy"]
        else:
            pool = _INTROSPECTION_RESPONSES["good"]

        base = random.choice(pool)

        if nrg < 20 and emo == "neutral" and pool == _INTROSPECTION_RESPONSES["good"]:
            base = random.choice(_INTROSPECTION_RESPONSES["low_energy"])

        return base

    @staticmethod
    def get_did_i_hurt_response() -> str:
        return random.choice(_INTROSPECTION_RESPONSES["did_i_hurt"])