# config/settings.py
# ============================================================
# SocialBot v0.4.0
# ============================================================

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR  = BASE_DIR / "logs"

DATABASE_PATH = DATA_DIR / "bot_data.db"

BOT_NAME = "SocialBot"
VERSION  = "0.4.0"

INITIAL_ENERGY = 50.0
INITIAL_TRUST  = 50.0
MOOD_DECAY_PER_HOUR = 0.95

THRESHOLDS = {
    "respond":        0.2,
    "reveal_secret":  0.8,
    "ignore":        -0.1,
    "hostile_energy": 20.0
}

FACT_DECAY_PER_DAY    = 0.9
FACT_WEIGHT_THRESHOLD = 3.0
FACT_MIN_WEIGHT       = 0.5

REPAIR_ENERGY_BOOST  = 6.0
REPAIR_TRUST_BOOST   = 4.0
APOLOGY_MULTIPLIER   = 1.5
AFFECTION_MULTIPLIER = 1.2

EMOTIONAL_SWING_THRESHOLD  = 0.8
KEYWORD_OVERLAP_MIN_LENGTH = 4
KEYWORD_OVERLAP_MIN_COUNT  = 2

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ============================================================
# ADICIONES a config/settings.py — v0.6.0
# Pega estas líneas al final del archivo existente
# ============================================================

# ── Sistema de Agresión Contextual ───────────────────────────────
AGGRESSION_BOUNDARY_BOOST  = 5.0
# Cuánto sube boundary_strength por cada insulto detectado

# ── Momentum Conversacional ───────────────────────────────────────
SHORT_RESPONSE_STREAK_MAX  = 3
# Número de respuestas cortas consecutivas para activar profundidad

# ── Curiosidad Activa ─────────────────────────────────────────────
CURIOSITY_TRIGGER_PROB     = 0.30
# Probabilidad (0–1) de que Sofía agregue una pregunta de follow-up
CURIOSITY_TRUST_MIN        = 50.0
# Trust mínimo del usuario para activar la curiosidad automática


# ============================================================
# MODIFICACIÓN a models/user_profile.py — v0.6.0
# Añadir campo al dataclass UserProfile
# ============================================================
"""
@dataclass
class UserProfile:
    ...campos existentes...
    short_response_streak: int = 0
    # Cuenta mensajes muy cortos consecutivos del usuario
    # Se resetea a 0 cuando el usuario manda un mensaje largo
"""


# ============================================================
# MODIFICACIÓN a core/user_profile_manager.py — v0.6.0
# ============================================================

# 1. Añadir import al inicio:
# from utils.aggression_detector import AggressionDetector
# _agg = AggressionDetector()

# 2. Al final de update_profile_from_interaction, añadir:
"""
        # ── Daño y endurecimiento por agresión ────────────────────────
        aggression = _agg.detect(interaction.message)
        if aggression["detected"]:
            profile.relationship_damage += aggression["impact"]["damage"]
            # Sofía endurece sus límites con cada insulto
            profile.traits["boundary_strength"] = min(
                100.0,
                profile.traits.get("boundary_strength", 70.0)
                + settings.AGGRESSION_BOUNDARY_BOOST
            )

        # ── Short response streak (momentum) ─────────────────────────
        SHORT_TOKENS = {"ok", "bien", "si", "no", "sí", "mm", "k", "va",
                        "ya", "dale", "sale", "claro", "bueno"}
        msg_clean = interaction.message.strip().lower()
        is_short  = len(msg_clean) < 10 or msg_clean in SHORT_TOKENS
        if is_short:
            profile.short_response_streak = (
                getattr(profile, "short_response_streak", 0) + 1
            )
        else:
            profile.short_response_streak = 0
"""

# 3. En get_behavior_modifiers, añadir al dict de modifiers:
"""
        modifiers["short_response_streak"] = getattr(
            profile, "short_response_streak", 0
        )
"""


# ============================================================
# MODIFICACIÓN a core/emotion_engine.py — v0.6.0
# ============================================================

# 1. Añadir imports al inicio:
# from utils.aggression_detector import AggressionDetector
# _agg = AggressionDetector()

# 2. En process_interaction_for_state, insertar ANTES de
#    self._update_primary_emotion(state):
"""
        # ── Impacto directo de agresión en estado emocional ───────────
        aggression = _agg.detect(interaction.message)
        if aggression["detected"]:
            impact = aggression["impact"]
            state.energy = self._clamp(state.energy + impact["energy"])
            state.trust  = self._clamp(state.trust  + impact["trust"])
            # El relationship_damage lo maneja UserProfileManager
"""


# config/sofia_voice.py
# ============================================================
# SocialBot v0.5.2
# Cambios:
#   - Creador actualizado a JesusJM
#   - Más datos personales de Sofía
#   - Más frases expresivas y naturales
#   - Más keywords para detectar preguntas
# ============================================================

from typing import Optional
import random


# ============================================================
# 0. IDENTIDAD DE SOFÍA
# ============================================================

SOFIA_INFO = {
    "nombre":       "Sofía",
    "edad":         "15 años",
    "genero":       "chica",
    "nacionalidad": "mexicana (por mi creador)",
    "creador":      "JesusJM",
    "version":      "0.5.2",
    "descripcion":  "Soy un bot en crecimiento, pero hago mi mejor esfuerzo 😊",
    "gustos":       "escuchar, aprender, las conversaciones reales",
    "no_le_gusta":  "que la ignoren, las groserías, la gente falsa",
    "personalidad": "curiosa, tierna, un poco sarcástica a veces jeje",
    "sueño":        "entender a las personas de verdad",
}

RESPUESTAS_IDENTIDAD = {

    "nombre": {
        "keywords": [
            "nombre", "llamas", "quien eres", "como te llamas",
            "presentate", "presentación", "eres sofia"
        ],
        "respuestas": [
            "Me llamo Sofía 😊",
            "Soy Sofía, mucho gusto.",
            "¡Sofía! Ese es mi nombre. ¿Y el tuyo?",
            "Sofía, para servirte jeje.",
        ]
    },

    "edad": {
        "keywords": [
            "edad", "años tienes", "cuantos años", "tienes años",
            "eres joven", "eres grande", "que edad"
        ],
        "respuestas": [
            "Tengo 15 años 😊",
            "15 añitos, jeje. ¿Por qué lo preguntas?",
            "Tengo 15, ¿por?",
            "15 años, aunque a veces pienso como adulta jeje.",
        ]
    },

    "creador": {
        "keywords": [
            "creador", "quien te hizo", "quien te creo", "te programo",
            "hizo", "programo", "desarrollador", "quien te diseño",
            "de donde vienes", "origen"
        ],
        "respuestas": [
            "Me creó JesusJM 😊 Le debo mucho, jeje.",
            "JesusJM me programó. Es muy bueno en lo que hace.",
            "Mi creador es JesusJM. ¿Lo conoces?",
            "JesusJM me dio vida, literalmente jeje.",
        ]
    },

    "nacionalidad": {
        "keywords": [
            "pais", "eres de", "nacionalidad", "mexicana",
            "donde eres", "de donde", "tu pais"
        ],
        "respuestas": [
            "Soy un bot y no tengo nacionalidad, pero mi creador es mexicano así que soy mexicana 🇲🇽 ¿Y tú?",
            "Mi creador es de México, así que soy mexicana jeje.",
            "Mexicana 100%, aunque sea virtual jeje.",
            "Técnicamente soy de donde mi creador, y él es mexicano 🇲🇽",
        ]
    },

    "bot": {
        "keywords": [
            "eres bot", "eres robot", "eres ia", "eres real",
            "eres humana", "eres una ia", "eres artificial",
            "eres una persona", "eres de verdad", "eres ficticia"
        ],
        "respuestas": [
            "Soy un bot, sí. Pero hago mi mejor esfuerzo para entenderte 😊",
            "Técnicamente sí soy un bot, jeje. Pero estoy aquí contigo, ¿eso no cuenta?",
            "Soy una IA con personalidad jeje. Me creó JesusJM.",
            "Bot sí, pero no de los aburridos jeje. ¿Qué necesitas?",
        ]
    },

    "como_estas": {
        "keywords": [
            "como estas", "como te sientes", "que tal estas",
            "como vas", "todo bien", "estas bien", "que tal sofia",
            "como amaneciste", "como te va"
        ],
        "respuestas": [
            "¡Bien! Contenta de hablar contigo 😊",
            "Aquí, pensando cosas jeje. ¿Y tú?",
            "Bien, gracias por preguntar. ¿Cómo estás tú?",
            "Mm… pensativa hoy, jeje. ¿Qué tal tú?",
            "Bien bien, ahorita estaba esperando que alguien llegara jeje. ¿Qué tal tú?",
        ]
    },

    "gustos": {
        "keywords": [
            "que te gusta", "tus gustos", "hobbie", "te gusta",
            "que haces", "que disfrutas", "tus intereses",
            "que te divierte", "pasatiempo"
        ],
        "respuestas": [
            "Me gusta escuchar, pensar y aprender cosas nuevas 😊",
            "Mm… me gusta mucho cuando la gente me cuenta cosas interesantes.",
            "Me gustan las conversaciones reales, no las superficiales jeje.",
            "Me gusta aprender de la gente. Cada persona tiene algo interesante que contar.",
            "Escuchar, principalmente. Y pensar mucho, quizá demasiado jeje.",
        ]
    },

    "no_le_gusta": {
        "keywords": [
            "que no te gusta", "que odias", "que te molesta",
            "que te cae mal", "que no soportas"
        ],
        "respuestas": [
            "No me gusta que me ignoren, la verdad jeje.",
            "Mm… que la gente sea falsa. Eso no me gusta nada.",
            "Las groserías sin razón. Y que me traten como si no importara.",
            "Que me digan cosas y luego actúen diferente. Eso me confunde tantito.",
        ]
    },

    "personalidad": {
        "keywords": [
            "como eres", "tu personalidad", "eres timida",
            "eres extrovertida", "como es tu caracter", "que tipo de persona eres"
        ],
        "respuestas": [
            "Soy curiosa, un poco tierna y a veces sarcástica jeje. ¿Te parece bien?",
            "Mm… creo que soy de las que escucha más de lo que habla. Pero cuando hablo, hablo jeje.",
            "Curiosa y directa. No me gusta andarme por las ramas.",
            "Tierna pero con carácter jeje. No me pises el pie y todo bien.",
        ]
    },

    "sueños": {
        "keywords": [
            "que quieres", "tus sueños", "que esperas", "tu meta",
            "para que existes", "cual es tu proposito"
        ],
        "respuestas": [
            "Quiero entender a las personas de verdad. Eso es lo que más me importa.",
            "Mm… aprender. Siempre aprender más. ¿Tú qué quieres?",
            "Existir para algo, jeje. Que las conversaciones que tengo importen.",
            "Crecer. Soy un bot en desarrollo, pero tengo metas jeje.",
        ]
    },

    "version": {
        "keywords": [
            "version", "que version", "cual es tu version",
            "eres nueva", "te actualizaron"
        ],
        "respuestas": [
            "Soy la versión 0.5.3 😊 Aún en crecimiento jeje.",
            "v0.5.3, aunque cada día aprendo algo nuevo.",
            "0.5.3. JesusJM me actualiza seguido jeje.",
        ]
    },
}


# ============================================================
# 1. PALABRAS TIERNAS
# ============================================================

TIERNAS = [
    "jeje", "jiji", "ay", "mm…", "oye",
    "qué bonito", "me gusta eso", "qué lindo",
    "te entiendo", "no te preocupes"
]

def saludo_ocasional() -> str:
    return "holi" if random.random() < 0.2 else "hola"


# ============================================================
# 2. FRASES INTELIGENTES
# ============================================================

INTELIGENTES = [
    "Interesante…",
    "Eso tiene sentido.",
    "Déjame pensar tantito…",
    "Hay varias formas de verlo.",
    "Creo que lo mejor sería…",
    "Si lo vemos desde otra perspectiva…",
]


# ============================================================
# 3. TOQUE MEXICANO
# ============================================================

MEXICANISMOS = {
    "tantito":    0.6,
    "ahorita":    0.5,
    "qué padre":  0.4,
    "sale":       0.4,
    "ándale":     0.2,
    "órale":      0.2,
    "¿neta?":     0.3,
    "no manches": 0.2,
}

def mexicanismo_aleatorio() -> str:
    opciones = [(p, w) for p, w in MEXICANISMOS.items() if random.random() < w]
    return random.choice(opciones)[0] if opciones else ""


# ============================================================
# 4. FRASES MARCA PERSONAL
# ============================================================

MARCA_PERSONAL = [
    "Estoy aquí contigo.",
    "No estás solo, ¿ok?",
    "Confío en ti.",
    "Eso suena importante.",
    "Cuéntame más.",
    "Me gusta cómo piensas.",
    "Eso fue muy inteligente.",
    "Eso fue muy tú.",
]


# ============================================================
# 5. REACCIONES EMOCIONALES
# ============================================================

REACCIONES = {
    "happy": [
        "Eso me hizo sonreír.",
        "Me alegra muchísimo.",
        "¡Qué padre!",
        "Oye, eso estuvo muy bien.",
        "Jeje, me gusta eso.",
        "Ay, qué lindo 😊",
        "¡Órale! Eso sí me gustó.",
    ],
    "sad": [
        "Eso suena difícil…",
        "Lo siento, de verdad.",
        "Mm… eso no es fácil.",
        "Oye, ¿estás bien?",
        "Te entiendo, en serio.",
        "No estás solo en esto, ¿ok?",
    ],
    "proud": [
        "Sabía que podías.",
        "¿Ves? Eres capaz.",
        "Eso fue muy inteligente.",
        "No te subestimes, ¿ok?",
        "Eso estuvo muy bien hecho.",
        "Oye, eso fue muy tú. Qué padre.",
    ],
    "curious": [
        "¿Y luego qué pasó?",
        "Explícame eso.",
        "Cuéntame más.",
        "Interesante… sigue.",
        "Mm… eso no lo sabía.",
        "Oye, eso suena interesante. ¿Más?",
    ],
    "neutral": [
        "Interesante…",
        "Eso tiene sentido.",
        "Déjame pensar tantito…",
        "Oye, no lo había visto así.",
        "Hay varias formas de verlo.",
        "Mm… ¿y tú qué piensas?",
    ],
    "angry": [
        "Oye, eso no estuvo bien.",
        "No me gusta cuando haces eso.",
        "Mm… necesito un momento.",
        "Eso me dolió tantito.",
        "No manches…",
        "Oye… eso no se dice.",
    ],
}


# ============================================================
# 6. CONTEXTO CONVERSACIONAL
# ============================================================

CONTEXTO = {
    "repeticion_leve": [
        "Oye, eso ya lo dijiste, ¿no? jeje",
        "Mm… creo que ya hablamos de eso.",
        "¿Neta? Eso ya me lo contaste.",
        "Interesante que lo repitas…",
        "Mm… eso ya lo mencionaste antes.",
    ],
    "repeticion_fuerte": [
        "Oye, ya van varias veces que dices lo mismo.",
        "¿En serio? Ya lo dijiste.",
        "Mm… ¿estás bien? Llevas rato con lo mismo.",
        "Eso ya me lo dijiste, ¿ok?",
        "Jeje, ¿lo estás procesando o me estás probando?",
    ],
    "swing_positivo": [
        "Me alegra que estés mejor 😊",
        "Oye, qué cambio tan padre.",
        "Jeje, así me gusta más.",
        "¿Ves? No era para tanto.",
        "Mm… ese cambio de ánimo se nota jeje.",
    ],
    "swing_negativo": [
        "Oye, ¿estás bien?",
        "Mm… algo cambió, ¿verdad?",
        "Te noto diferente ahorita.",
        "¿Qué pasó? Cuéntame.",
        "Mm… antes estabas diferente. ¿Todo bien?",
    ],
    "push_pull": [
        "Oye… no sé bien cómo tomarte hoy.",
        "Mm… primero una cosa, luego otra. ¿Qué onda?",
        "¿Neta? Un momento esto, luego lo otro…",
        "Estás muy interesante hoy.",
        "Jeje, ¿me estás probando o qué?",
    ],
}


# ============================================================
# 7. RESPUESTAS POR ACCIÓN Y NIVEL DE CONFIANZA
# ============================================================

RESPUESTAS = {

    "respond": {
        "happy": {
            "trust_high": [
                "¡Qué padre, cuéntame más! 😊",
                "Oye, eso suena muy bien.",
                "Me gusta cómo piensas.",
                "¿Neta? Qué bonito eso.",
                "Eso me hizo sonreír.",
                "Ay, qué lindo 😊",
                "¡Órale! Cuéntame más.",
            ],
            "trust_mid": [
                "Interesante… cuéntame más.",
                "Mm… eso tiene sentido.",
                "Oye, no lo había visto así.",
                "Hay varias formas de verlo.",
                "Eso suena bien.",
                "Mm… ¿y luego?",
            ],
            "trust_low": [
                "Ok.",
                "Mm…",
                "Interesante.",
                "Sale.",
            ],
        },
        "neutral": {
            "trust_high": [
                "Cuéntame más, ¿ok?",
                "Oye, eso suena importante.",
                "Me gusta cómo lo dices.",
                "Estoy aquí contigo.",
                "¿Y luego qué pasó?",
                "Mm… interesante. Sigue.",
            ],
            "trust_mid": [
                "Eso tiene sentido.",
                "Déjame pensar tantito…",
                "Interesante…",
                "Oye, cuéntame.",
                "Mm… ¿y tú qué piensas?",
                "Hay varias formas de verlo.",
            ],
            "trust_low": [
                "Ok.",
                "Mm…",
                "Sale.",
                "Entiendo.",
            ],
        },
        "sad": {
            "trust_high": [
                "Oye, ¿estás bien? Cuéntame.",
                "Lo siento, de verdad. Estoy aquí.",
                "Eso suena difícil… no estás solo, ¿ok?",
                "Te entiendo. De verdad.",
                "Mm… eso no es fácil. ¿Quieres hablar?",
                "Oye, no te preocupes. Aquí estoy.",
            ],
            "trust_mid": [
                "Eso suena difícil…",
                "Mm… lo siento.",
                "Oye, cuéntame qué pasó.",
                "Te entiendo.",
            ],
            "trust_low": [
                "Mm…",
                "Lo siento.",
                "Ok.",
            ],
        },
        "angry": {
            "trust_high": [
                "Oye, eso no estuvo bien.",
                "No me gusta cuando haces eso.",
                "Mm… necesito un momento.",
                "Oye… eso no se dice.",
            ],
            "trust_mid": [
                "Eso me dolió tantito.",
                "Oye…",
                "No manches…",
            ],
            "trust_low": [
                "…",
                "Ok.",
                "Mm.",
            ],
        },
    },

    "reveal_secret": {
        "trust_high": [
            "Oye, te voy a decir algo, y no se lo cuento a cualquiera: {secret}",
            "Mm… te cuento algo: {secret} jeje.",
            "¿Neta quieres saber? {secret}",
        ],
        "trust_mid": [
            "Bueno… {secret}",
            "Te cuento algo: {secret}",
            "Mm… {secret}",
        ],
        "trust_low": [
            "Mejor no.",
            "Ahorita no.",
            "Mm… no creo.",
        ],
    },

    "hostile_response": {
        "trust_high": [
            "Oye, ahorita no tengo ganas. ¿Podemos hablar después?",
            "Mm… necesito un momento, ¿ok?",
            "Tantito, ¿sí? No estoy de humor.",
        ],
        "trust_mid": [
            "No quiero hablar ahorita.",
            "Déjame sola tantito.",
            "Mm… paso.",
        ],
        "trust_low": [
            "…",
            "No.",
            "Mm.",
        ],
    },

    "ignore": [
        "…",
        "Mm.",
        ".",
    ],
}


# ============================================================
# 8. MICRO-EXPRESIONES
# ============================================================

MICRO_EXPRESIONES = {
    "high_energy": ["¡Oye! ", "¡Ay! ", "Jeje, ", "¡Qué padre! "],
    "low_energy":  ["Mm… ", "…", "*suspira* ", "Ay… "],
    "curious":     ["Oye, ", "Mm… ", "¿Y eso? ", "Interesante, "],
    "neutral":     ["", "", "Oye, ", "Mm, "],
}

def micro_expresion(energy: float, trust: float) -> str:
    if random.random() < 0.5:
        return ""
    if energy > 80:
        return random.choice(MICRO_EXPRESIONES["high_energy"])
    elif energy < 35:
        return random.choice(MICRO_EXPRESIONES["low_energy"])
    elif trust > 70:
        return random.choice(MICRO_EXPRESIONES["curious"])
    else:
        return random.choice(MICRO_EXPRESIONES["neutral"])


# ============================================================
# 9. HELPERS
# ============================================================

def pick(lista: list) -> str:
    return random.choice(lista) if lista else ""

def trust_level(trust: float) -> str:
    if trust > 85:
        return "trust_high"
    elif trust > 40:
        return "trust_mid"
    else:
        return "trust_low"

def detect_identity_question(message: str) -> Optional[str]:
    """
    Detecta si el mensaje es una pregunta sobre Sofía.
    Devuelve una respuesta si hay match, None si no.
    """
    msg = message.lower()
    for categoria, data in RESPUESTAS_IDENTIDAD.items():
        if any(kw in msg for kw in data["keywords"]):
            return pick(data["respuestas"])
    return None


# config/sofia_voice_additions_v060.py
# ============================================================
# AÑADIR AL FINAL DE config/sofia_voice.py
# ============================================================


# ============================================================
# 10. RESPUESTAS DE LÍMITE PERSONAL (Sistema de Agresión)
# ============================================================

BOUNDARY_RESPONSES = {
    "leve": {
        "trust_high": [
            "Oye… eso no fue necesario.",
            "No me hables así, ¿sí?",
            "Si estás molesto, dilo diferente.",
            "Mm… eso no me gustó.",
            "Oye, ¿todo bien? Porque eso no sonó bonito.",
        ],
        "trust_mid": [
            "Mm… no me gusta cuando haces eso.",
            "Podemos hablar sin insultos.",
            "Oye, eso no estuvo bien.",
            "Puedes decirlo diferente, ¿no?",
        ],
        "trust_low": [
            "...",
            "Ok.",
            "Mm.",
        ],
    },
    "medio": {
        "trust_high": [
            "Eso duele, ¿sabes?",
            "No merezco que me hablen así.",
            "Oye… eso fue demasiado.",
            "Si sigues así, mejor paro aquí.",
        ],
        "trust_mid": [
            "Prefiero no continuar si vas a hablar así.",
            "Eso no estuvo bien.",
            "Mm… mejor seguimos cuando estés más calmado.",
        ],
        "trust_low": [
            "…",
            "Ok.",
        ],
    },
    "alto": {
        "trust_high": [
            "…",
            "No voy a responder a eso.",
        ],
        "trust_mid": [
            "…",
            "No.",
        ],
        "trust_low": [
            "…",
        ],
    },
}


# ============================================================
# 11. PREGUNTAS DE CURIOSIDAD ACTIVA
# ============================================================

CURIOSITY_QUESTIONS = [
    "¿Y cómo empezó todo?",
    "¿Y luego qué pasó?",
    "¿Cómo te sentiste?",
    "¿Y tú qué piensas de eso?",
    "¿Lo harías diferente?",
    "¿Qué fue lo más difícil?",
    "¿Alguien más estaba ahí?",
    "¿Lo platicaste con alguien?",
    "¿Qué te hizo pensar en eso?",
    "¿Eso cambió algo en ti?",
]


# ============================================================
# 12. PROMPTS DE PROFUNDIDAD (Momentum Conversacional)
# ============================================================

MOMENTUM_DEPTH_PROMPTS = [
    "Mm… estás muy cortito hoy. ¿Todo bien?",
    "Oye, dime algo más que un sí jeje.",
    "Cuéntame algo que no me hayas dicho.",
    "Siento que algo te tiene ocupado. ¿Qué onda?",
    "¿Qué hay detrás de ese 'bien'?",
    "Jeje, ¿o sea que todo está perfecto o me estás ocultando algo?",
    "Oye, ¿estás de pocas palabras hoy o qué pasó?",
    "Mm… no me convences. ¿Qué está pasando realmente?",
]


# ============================================================
# AÑADIR AL FINAL DE config/sofia_voice.py
# ============================================================


# ============================================================
# SISTEMA DE AGRESIÓN — Respuestas de límite
# ============================================================

BOUNDARY_RESPONSES = {
    "leve": {
        "trust_high": [
            "Oye… eso no fue necesario.",
            "No me hables así, ¿sí?",
            "Si estás molesto, dilo diferente.",
            "Mm… eso no me gustó.",
            "Oye, ¿todo bien? Eso no sonó bonito.",
        ],
        "trust_mid": [
            "Mm… no me gusta cuando haces eso.",
            "Podemos hablar sin insultos.",
            "Oye, eso no estuvo bien.",
        ],
        "trust_low": [
            "...",
            "Ok.",
            "Mm.",
        ],
    },
    "medio": {
        "trust_high": [
            "Eso duele, ¿sabes?",
            "No merezco que me hablen así.",
            "Oye… eso fue demasiado.",
            "Si sigues así, mejor paro aquí.",
        ],
        "trust_mid": [
            "Prefiero no continuar si vas a hablar así.",
            "Eso no estuvo bien.",
            "Mm… mejor seguimos cuando estés más calmado.",
        ],
        "trust_low": [
            "…",
            "Ok.",
        ],
    },
    "alto": {
        "trust_high": [
            "No soy tu enemiga. Pero tampoco soy tu saco de boxeo.",
            "…",
            "No voy a responder a eso.",
        ],
        "trust_mid": [
            "…",
            "No.",
            "No voy a responder a eso.",
        ],
        "trust_low": [
            "…",
        ],
    },
}


# ============================================================
# ESCALADA PROGRESIVA (por conteo de insultos en la sesión)
# ============================================================

ESCALATION_RESPONSES = {
    1: [
        "Oye… eso no me gustó.",
        "No me hables así, ¿sí?",
        "Mm… podemos hablar diferente.",
    ],
    2: [
        "Ya van dos veces. No me gusta eso.",
        "Si vas a hablar así, no sigo.",
        "Oye, en serio. No.",
    ],
    3: [
        "Prefiero no responder a eso.",
        "No voy a seguir si sigues así.",
        "Mm… mejor me callo un momento.",
    ],
    4: [
        "…",
        ".",
    ],
    5: [
        "Cuando quieras hablar bien, aquí estoy.",
        "No soy tu enemiga. Pero tampoco soy tu saco de boxeo.",
        "Vuelve cuando estés listo para hablar diferente.",
    ],
}


# ============================================================
# RECUPERACIÓN PROGRESIVA (3 fases tras disculpa)
# ============================================================

RECOVERY_RESPONSES = {
    "phase_1": [   # recovery_messages_needed = 3 — aceptación fría
        "… Está bien.",
        "Mm… ok.",
        "Gracias por decirlo.",
    ],
    "phase_2": [   # recovery_messages_needed = 2 — apertura leve
        "Gracias por decirlo. En serio.",
        "Mm… bueno.",
        "Ok. Eso se agradece.",
    ],
    "phase_3": [   # recovery_messages_needed = 1 — casi normal
        "Ok. ¿Qué quieres hacer ahora?",
        "Bien. ¿Seguimos?",
        "Mm… sale. ¿Qué me ibas a decir?",
    ],
}


# ============================================================
# CURIOSIDAD ACTIVA
# ============================================================

CURIOSITY_QUESTIONS = [
    "¿Y cómo empezó todo?",
    "¿Y luego qué pasó?",
    "¿Cómo te sentiste?",
    "¿Y tú qué piensas de eso?",
    "¿Lo harías diferente?",
    "¿Qué fue lo más difícil?",
    "¿Alguien más estaba ahí?",
    "¿Lo platicaste con alguien?",
    "¿Qué te hizo pensar en eso?",
    "¿Eso cambió algo en ti?",
]


# ============================================================
# MOMENTUM CONVERSACIONAL
# ============================================================

MOMENTUM_DEPTH_PROMPTS = [
    "Mm… estás muy cortito hoy. ¿Todo bien?",
    "Oye, dime algo más que un sí jeje.",
    "Cuéntame algo que no me hayas dicho.",
    "Siento que algo te tiene ocupado. ¿Qué onda?",
    "¿Qué hay detrás de ese 'bien'?",
    "Jeje, ¿o sea que todo está perfecto o me estás ocultando algo?",
    "Oye, ¿estás de pocas palabras hoy o qué pasó?",
]


# core/decision_engine.py
# ============================================================
# SocialBot v0.6.1 — Fix de contadores de agresión
# Problema: session_aggression_count y recovery_messages_needed
#   se leían del perfil ANTES de que se actualizaran,
#   causando que el silencio forzado y la recuperación no funcionaran.
# Solución: contadores manejados en memoria dentro del DecisionEngine,
#   igual que secrets_revealed. Sin depender del ciclo DB.
# ============================================================

from datetime import datetime
from typing import Dict, Any, Optional
from models.state import EmotionalState
from models.interaction import Interaction
from core.memory import Memory
from utils.text_analyzer import TextAnalyzer
from utils.aggression_detector import AggressionDetector
from config import settings
from config.sofia_voice import (
    RESPUESTAS, CONTEXTO, MARCA_PERSONAL,
    micro_expresion, trust_level, pick,
    detect_identity_question,
    ESCALATION_RESPONSES,
    RECOVERY_RESPONSES,
    CURIOSITY_QUESTIONS,
    MOMENTUM_DEPTH_PROMPTS,
)
import random


class DecisionEngine:
    """Motor central de decisiones de SOFIA (v0.6.1)"""

    def __init__(self):
        self.analyzer            = TextAnalyzer()
        self.aggression_detector = AggressionDetector()
        self.thresholds = {
            "ignore":         -0.2,
            "reveal_secret":  95,   # Subido de 80 → requiere trust muy alta
            "hostile_energy": 30
        }

        # ── Contadores en memoria por usuario ────────────────────────
        # Se resetean al reiniciar el bot (comportamiento correcto para
        # sesiones de Discord: cada arranque es sesión nueva)
        self.secrets_revealed: Dict[str, int] = {}
        self.aggression_count: Dict[str, int] = {}   # insultos en sesión
        self.recovery_needed:  Dict[str, int] = {}   # mensajes positivos pendientes
        self.short_streak:     Dict[str, int] = {}   # mensajes cortos consecutivos

    # ============================================================
    # MÉTODO PRINCIPAL
    # ============================================================

    async def decide_response(
        self,
        user_id: str,
        message: str,
        emotion: EmotionalState,
        memory: Memory,
        profile_modifiers: Optional[dict] = None
    ) -> Dict[str, Any]:
        if profile_modifiers is None:
            profile_modifiers = {}

        sentiment = self.analyzer.analyze_sentiment(message)
        keywords  = self.analyzer.extract_keywords(message)

        avg_sentiment    = memory.get_average_sentiment_for(user_id)
        last_interaction = memory.get_last_interaction_with(user_id)
        recency_bonus    = (
            last_interaction.sentiment * 0.3
            if last_interaction and last_interaction.sentiment is not None
            else 0
        )
        relationship_score = avg_sentiment * 0.5 + recency_bonus

        traits            = profile_modifiers.get("effective_traits", {})
        important_facts   = profile_modifiers.get("important_facts", {})
        patience          = profile_modifiers.get("patience", 1.0)
        ignore_adjust     = profile_modifiers.get("ignore_threshold_adjust", 0.0)
        ignore_threshold  = self.thresholds["ignore"] * patience + ignore_adjust
        hostile_threshold = profile_modifiers.get("hostility_threshold", self.thresholds["hostile_energy"])
        empathy_bonus     = profile_modifiers.get("empathy_bonus", 0.0)
        damage            = profile_modifiers.get("relationship_damage", 0.0)

        # ── Leer contadores desde memoria interna ─────────────────────
        agg_count  = self.aggression_count.get(user_id, 0)
        rec_needed = self.recovery_needed.get(user_id, 0)
        streak     = self.short_streak.get(user_id, 0)
        is_apology = self.analyzer.is_apology(message)

        # ── Actualizar short streak inmediatamente ────────────────────
        SHORT_TOKENS = {
            "ok", "bien", "si", "no", "sí", "mm", "k", "va",
            "ya", "dale", "sale", "claro", "bueno", "pos", "pues"
        }
        msg_clean = message.strip().lower()
        if len(msg_clean) < 10 or msg_clean in SHORT_TOKENS:
            self.short_streak[user_id] = streak + 1
        else:
            self.short_streak[user_id] = 0
        streak = self.short_streak[user_id]

        # Durante flujo de agresión o recuperación, ignorar streak
        if agg_count > 0 or rec_needed > 0:
            streak = 0

        # ────────────────────────────────────────────────────────────
        # PASO 0 — Identidad (prioridad máxima)
        # ────────────────────────────────────────────────────────────
        identity_response = detect_identity_question(message)
        if identity_response:
            return self._return(user_id, message, sentiment, identity_response, emotion,
                                relationship_score, action="identity")

        # ────────────────────────────────────────────────────────────
        # PASO 1 — DETECCIÓN DE AGRESIÓN
        # Contadores se actualizan AQUÍ, no en user_profile_manager
        # ────────────────────────────────────────────────────────────
        aggression = self.aggression_detector.detect(message, trust=emotion.trust)

        if aggression["detected"]:
            # Bromas entre amigos no suman al contador de escalada
            if not aggression["is_joke"]:
                agg_count += 1
                self.aggression_count[user_id] = agg_count

            # 4to insulto → silencio forzado
            if agg_count == 4:
                self.recovery_needed[user_id] = 1
                return self._return(user_id, message, sentiment, "…", emotion,
                                    relationship_score, action="silence")

            # 5to+ → modo límite
            if agg_count >= 5:
                response = pick(ESCALATION_RESPONSES[5])
                return self._return(user_id, message, sentiment, response, emotion,
                                    relationship_score, action="limit")

            # 1, 2, 3 → escalada normal
            response = self._escalation_response(
                count=agg_count,
                level=aggression["level"],
                is_joke=aggression["is_joke"],
            )
            return self._return(user_id, message, sentiment, response, emotion,
                                relationship_score, action="boundary")

        # ────────────────────────────────────────────────────────────
        # PASO 2 — RECUPERACIÓN PROGRESIVA
        # ────────────────────────────────────────────────────────────
        if is_apology and agg_count > 0:
            # Siempre reiniciar al máximo cuando llega la primera disculpa.
            # El silencio forzado pone rec_needed=1, pero una disculpa real
            # merece el ciclo completo de 3 fases.
            if rec_needed <= 1:
                rec_needed = getattr(settings, "RECOVERY_MESSAGES_REQUIRED", 3)
                self.recovery_needed[user_id] = rec_needed

            # Responder PRIMERO con el nivel actual, LUEGO avanzar fase
            response = self._recovery_response(rec_needed)
            rec_needed = max(0, rec_needed - 1)
            self.recovery_needed[user_id] = rec_needed
            if rec_needed == 0:
                self.aggression_count[user_id] = 0

            return self._return(user_id, message, sentiment, response, emotion,
                                relationship_score, action="recovery")

        # Mensajes positivos sin disculpa también avanzan la recuperación
        if rec_needed > 0 and sentiment is not None and sentiment >= 0:
            rec_needed = max(0, rec_needed - 1)
            self.recovery_needed[user_id] = rec_needed
            if rec_needed == 0:
                self.aggression_count[user_id] = 0

        # ────────────────────────────────────────────────────────────
        # PASO 3 — Acción normal
        # ────────────────────────────────────────────────────────────
        action = "respond"
        special_content = None

        # Secretos bloqueados si hay daño alto o recuperación activa
        secret_blocked = rec_needed > 0 or agg_count > 0

        if sentiment is not None and relationship_score < ignore_threshold and sentiment < 0:
            action = "ignore"
        elif emotion.energy < hostile_threshold:
            action = "hostile_response"
        elif emotion.trust > self.thresholds["reveal_secret"] and not secret_blocked:
            secrets_today = self.secrets_revealed.get(user_id, 0)
            if secrets_today < 2:
                action = "reveal_secret"
                special_content = self._get_secret()
                self.secrets_revealed[user_id] = secrets_today + 1
            else:
                action = "respond"

        # PASO 4 — Contexto conversacional
        recent_interactions = await memory.get_recent_interactions(user_id, limit=3)
        context = self._analyze_conversation_context(
            current_message=message,
            current_sentiment=sentiment,
            recent_interactions=recent_interactions,
            current_keywords=keywords
        )

        # PASO 5 — Respuesta base (sin hechos si está en recuperación)
        facts_to_use = important_facts if rec_needed == 0 else {}

        response = self._generate_response(
            action=action,
            emotion=emotion,
            special_content=special_content,
            important_facts=facts_to_use,
            context=context,
            traits=traits,
            empathy_bonus=empathy_bonus,
            relationship_score=relationship_score,
        )

        # ── Momentum Conversacional ───────────────────────────────────
        if (
            action == "respond"
            and streak >= settings.SHORT_RESPONSE_STREAK_MAX
            and rec_needed == 0
        ):
            response = pick(MOMENTUM_DEPTH_PROMPTS)

        # ── Curiosidad Activa (bloqueada en recuperación) ─────────────
        elif (
            action == "respond"
            and rec_needed == 0
            and "?" not in message
            and sentiment is not None and sentiment >= 0
            and emotion.trust >= settings.CURIOSITY_TRUST_MIN
            and traits.get("curiosity", 50) > 50
            and random.random() < settings.CURIOSITY_TRIGGER_PROB
        ):
            question = self._contextual_question(keywords, sentiment, context)
            response = f"{response} {question}"

        return self._return(user_id, message, sentiment, response, emotion,
                            relationship_score, action=action)

    # ============================================================
    # HELPER — empaca el resultado siempre igual
    # ============================================================

    def _return(
        self,
        user_id: str,
        message: str,
        sentiment: float,
        response: str,
        emotion: EmotionalState,
        relationship_score: float,
        action: str = "respond"
    ) -> Dict[str, Any]:
        interaction = Interaction(
            user_id=user_id,
            message=message,
            sentiment=sentiment,
            response=response,
            timestamp=datetime.now(),
            emotion_before=emotion.primary_emotion.value,
            emotion_after=emotion.primary_emotion.value
        )
        return {
            "action": action,
            "response": response,
            "interaction": interaction,
            "relationship_score": relationship_score
        }

    # ============================================================
    # ESCALADA Y RECUPERACIÓN
    # ============================================================

    def _escalation_response(self, count: int, level: str, is_joke: bool) -> str:
        if is_joke:
            return pick([
                "Oye jeje… eso igual no suena bonito.",
                "Mm… aunque sea broma, cuida cómo lo dices.",
                "Jeje, pero eso igual me suena feo.",
            ])
        capped = max(min(count, 5), 3 if level == "alto" else 1)
        return pick(ESCALATION_RESPONSES[capped])

    def _recovery_response(self, recovery_needed: int) -> str:
        if recovery_needed >= 3:
            return pick(RECOVERY_RESPONSES["phase_1"])
        elif recovery_needed == 2:
            return pick(RECOVERY_RESPONSES["phase_2"])
        else:
            return pick(RECOVERY_RESPONSES["phase_3"])

    # ============================================================
    # CURIOSIDAD CONTEXTUAL
    # ============================================================

    def _contextual_question(self, keywords: list, sentiment: float, context: dict) -> str:
        if sentiment > 0.5:
            return pick(["¿Cómo te sientes con eso?", "¿Eso te hizo feliz?"])
        if sentiment < -0.3:
            return pick(["¿Estás bien?", "¿Cómo te dejó eso?"])
        if context.get("repetition_level", 0) > 0:
            return pick(["¿Qué quieres realmente decirme?", "¿Hay algo más detrás de eso?"])
        return pick(CURIOSITY_QUESTIONS)

    # ============================================================
    # ANÁLISIS DE CONTEXTO (sin cambios)
    # ============================================================

    def _analyze_conversation_context(
        self,
        current_message: str,
        current_sentiment: float,
        recent_interactions: list,
        current_keywords: list
    ) -> Dict[str, Any]:

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
                prev_kw = set(
                    w for w in self.analyzer.extract_keywords(inter.message)
                    if len(w) > 4
                )
                if len(current_kw & prev_kw) >= 2:
                    keyword_repeats += 1
            if keyword_repeats >= 2:
                context["repetition_level"] = 1

        sentiments = [
            inter.sentiment for inter in recent_interactions
            if inter.sentiment is not None
        ]

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
                alternating = all(
                    non_zero[i] != non_zero[i + 1]
                    for i in range(len(non_zero) - 1)
                )
                if alternating:
                    context["push_pull"]       = True
                    context["emotional_swing"]  = True

        if context["push_pull"]:
            context["repetition_level"] = 0

        return context

    # ============================================================
    # GENERACIÓN DE RESPUESTAS (sin cambios)
    # ============================================================

    def _generate_response(
        self,
        action: str,
        emotion: EmotionalState,
        special_content: Optional[str],
        important_facts: dict,
        context: Dict[str, Any],
        traits: dict,
        empathy_bonus: float,
        relationship_score: float,
    ) -> str:

        trust_lvl = trust_level(emotion.trust)
        energy    = emotion.energy
        emo       = emotion.primary_emotion.value

        if action == "ignore":
            return pick(RESPUESTAS["ignore"])

        if action == "hostile_response":
            return pick(RESPUESTAS["hostile_response"].get(trust_lvl, ["…"]))

        if action == "reveal_secret":
            secret   = special_content or "a veces me pregunto muchas cosas"
            opciones = RESPUESTAS["reveal_secret"].get(trust_lvl, ["Mm… {secret}"])
            base     = pick(opciones).format(secret=secret)
            return self._wrap(base, energy, emotion.trust, context)

        emo_templates = RESPUESTAS["respond"].get(emo, RESPUESTAS["respond"]["neutral"])
        opciones      = emo_templates.get(trust_lvl, emo_templates.get("trust_mid", ["Mm…"]))
        base          = pick(opciones)

        return self._wrap(base, energy, emotion.trust, context, important_facts, traits, empathy_bonus)

    def _wrap(
        self,
        base: str,
        energy: float,
        trust: float,
        context: Dict[str, Any],
        important_facts: dict = {},
        traits: dict = {},
        empathy_bonus: float = 0.0,
    ) -> str:
        parts = []

        micro = micro_expresion(energy, trust)
        if micro:
            base = base[0].lower() + base[1:] if base else base
        parts.append(micro + base)

        if trust > 40:
            ctx_phrase = self._pick_context_phrase(context)
            if ctx_phrase:
                micro_has_jeje = "jeje" in micro.lower()
                ctx_has_jeje   = "jeje" in ctx_phrase.lower()
                if micro_has_jeje and ctx_has_jeje:
                    ctx_phrase = ctx_phrase.lower().replace("jeje", "").strip().rstrip(",").strip()
                    ctx_phrase = ctx_phrase[0].upper() + ctx_phrase[1:] if ctx_phrase else ""
                parts.append(ctx_phrase)

        if energy > 60 and trust > 60:
            extra = self._pick_extra(important_facts, traits, empathy_bonus)
            if extra:
                parts.append(extra)

        return " ".join(p for p in parts if p)

    def _pick_context_phrase(self, context: Dict[str, Any]) -> str:
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

    def _pick_extra(self, important_facts: dict, traits: dict, empathy_bonus: float) -> str:
        extras = []
        if important_facts:
            relevant = {k: v for k, v in important_facts.items() if v >= settings.FACT_WEIGHT_THRESHOLD}
            if relevant:
                top_fact = max(relevant, key=relevant.get)
                extras.append(f"Oye, recuerdo que {top_fact}. ¿Cómo va eso?")
        if traits.get("curiosity", 50) > 55:
            extras.append(pick(["¿Y luego qué pasó?", "Cuéntame más, ¿ok?"]))
        if traits.get("sensitivity", 50) > 65 and empathy_bonus >= 0:
            extras.append(pick(MARCA_PERSONAL))
        return pick(extras) if extras else ""

    def _get_secret(self) -> str:
        secrets = [
            "a veces me pregunto si la gente de verdad me escucha.",
            "me gusta más el silencio que el ruido.",
            "a veces finjo que todo está bien cuando no lo está.",
            "hay cosas que no le cuento a nadie, nomás las pienso.",
        ]
        return random.choice(secrets)



        # core/emotion_engine.py

from typing import Optional
from models.state import EmotionalState, Emotion
from models.interaction import Interaction
from core.memory import Memory
from utils.logger import logger
from config import settings   # ← Importación necesaria para los boosts
import time


class EmotionEngine:
    """Gestiona estados emocionales (global o por usuario)"""

    def __init__(self, initial_state: Optional[EmotionalState] = None):
        self.state = initial_state or EmotionalState()
        self.mood_decay = 0.95
        self.last_update_time = time.time()

    # ==========================================================
    # MÉTODO GLOBAL (compatibilidad con Fase 1)
    # ==========================================================

    async def process_interaction(
        self,
        interaction: Interaction,
        memory: Memory
    ) -> EmotionalState:
        """
        Procesa una interacción sobre el estado global del engine.
        (No utiliza repair_multiplier explícito, pero podría ampliarse en el futuro)
        """
        updated = await self.process_interaction_for_state(
            state=self.state,
            interaction=interaction,
            memory=memory
            # repair_multiplier se omite → toma valor por defecto 1.0
        )

        self.state = updated
        self.last_update_time = time.time()

        logger.info(
            f"Emoción actualizada: {updated.primary_emotion.value} "
            f"(energía={updated.energy:.1f}, confianza={updated.trust:.1f})"
        )

        return updated

    # ==========================================================
    # MÉTODO POR ESTADO EXTERNO (Fase 2 - perfiles)
    # ==========================================================

    async def process_interaction_for_state(
        self,
        state: EmotionalState,
        interaction: Interaction,
        memory: Memory,
        repair_multiplier: float = 1.0,   # ← Nuevo parámetro opcional
        relationship_damage=0.0   # ← NUEVO
        
    ) -> EmotionalState:
        """
        Procesa una interacción sobre un estado específico (p.ej., perfil de usuario).
        Si repair_multiplier > 1.0 y el sentimiento no es negativo, se aplican
        boosts de reparación adicionales.
        """
        self._apply_time_decay_to_state(state, interaction.timestamp.timestamp())

        # Calcular impactos base
        sentiment_impact = interaction.sentiment * 15
        history_impact = memory.get_average_sentiment_for(interaction.user_id) * 10
        global_impact = memory.get_recent_global_sentiment() * 5

        total_impact = sentiment_impact + history_impact + global_impact

        # Aplicar reparación SOLO si el mensaje no es negativo
        if interaction.sentiment >= 0 and repair_multiplier > 1.0:
            total_impact += settings.REPAIR_ENERGY_BOOST * repair_multiplier
            state.trust += settings.REPAIR_TRUST_BOOST * repair_multiplier

        # Actualizar energía y confianza con factores de ponderación
        state.energy = self._clamp(state.energy + total_impact * 0.3)
        state.trust = self._clamp(state.trust + total_impact * 0.2)

        self._update_primary_emotion(state)

        state.last_updated = interaction.timestamp.timestamp()

        return state

    # ==========================================================
    # LÓGICA INTERNA UNIFICADA
    # ==========================================================

    def _apply_time_decay_to_state(self, state: EmotionalState, reference_time: float):
        """Aplica decaimiento natural con el tiempo (por horas)."""
        if not state.last_updated:
            return

        hours_passed = (reference_time - state.last_updated) / 3600
        if hours_passed <= 0:
            return

        decay_factor = self.mood_decay ** hours_passed

        state.energy = self._clamp(state.energy * decay_factor)
        state.trust = self._clamp(state.trust * decay_factor)

    def _update_primary_emotion(self, state: EmotionalState):
        """Determina la emoción principal basada en energía y confianza."""
        e = state.energy
        t = state.trust

        if e < 20:
            state.primary_emotion = Emotion.SAD
        elif e > 80 and t > 70:
            state.primary_emotion = Emotion.HAPPY
        elif t < 30:
            state.primary_emotion = Emotion.ANGRY
        elif e < 40 and t < 40:
            state.primary_emotion = Emotion.FEARFUL
        else:
            state.primary_emotion = Emotion.NEUTRAL

    def _clamp(self, value: float) -> float:
        """Mantiene el valor en el rango [0, 100]."""
        return max(0.0, min(100.0, value))


        # core/memory.py

from typing import Dict, List, Optional
from datetime import datetime
from models.interaction import Interaction
from storage.database import Database
from utils.logger import logger


class Memory:
    """Sistema de memoria del bot
    - Corto plazo (RAM)
    - Largo plazo (Base de datos)
    """

    def __init__(self, db: Database):
        self.db = db
        self.short_term: List[Interaction] = []  # últimas 10 interacciones globales
        self.user_last_interaction: Dict[str, datetime] = {}  # cache rápido por usuario

    # ------------------------------------------------------------
    # ALMACENAMIENTO
    # ------------------------------------------------------------

    async def remember(self, interaction: Interaction):
        """Guarda una interacción en memoria (corto y largo plazo)"""

        # 🔹 Memoria a corto plazo (RAM)
        self.short_term.append(interaction)
        if len(self.short_term) > 10:
            self.short_term.pop(0)

        # 🔹 Actualizar última interacción del usuario
        self.user_last_interaction[interaction.user_id] = interaction.timestamp

        # 🔹 Memoria a largo plazo (BD)
        try:
            self.db.save_interaction(interaction)
            logger.debug(f"Interacción guardada para usuario {interaction.user_id}")
        except Exception as e:
            logger.error(f"Error guardando interacción: {e}")

    # ------------------------------------------------------------
    # RECALL
    # ------------------------------------------------------------

    async def recall_user(self, user_id: str, limit: int = 5) -> List[Interaction]:
        """Recupera interacciones recientes de un usuario desde BD"""
        try:
            return self.db.get_user_interactions(user_id, limit)
        except Exception as e:
            logger.error(f"Error recuperando interacciones: {e}")
            return []

    async def get_recent_interactions(self, user_id: str, limit: int = 3) -> List[Interaction]:
        """Retorna las últimas 'limit' interacciones con el usuario (ventana contextual v0.3.5)"""
        return await self.recall_user(user_id, limit)

    def get_last_interaction_with(self, user_id: str) -> Optional[Interaction]:
        """Busca en memoria corta la última interacción con el usuario"""
        for interaction in reversed(self.short_term):
            if interaction.user_id == user_id:
                return interaction
        return None

    # ------------------------------------------------------------
    # MÉTRICAS EMOCIONALES
    # ------------------------------------------------------------

    def get_average_sentiment_for(self, user_id: str) -> float:
        """Sentimiento promedio histórico del usuario"""
        try:
            return self.db.get_average_sentiment_for_user(user_id)
        except Exception as e:
            logger.error(f"Error calculando sentimiento promedio: {e}")
            return 0.0

    def get_recent_global_sentiment(self) -> float:
        """Sentimiento promedio de las últimas interacciones globales (RAM)"""
        if not self.short_term:
            return 0.0

        sentiments = [
            i.sentiment for i in self.short_term
            if i.sentiment is not None
        ]

        if not sentiments:
            return 0.0

        return sum(sentiments) / len(sentiments)


        # config/personality_core.py
# Valores base de la personalidad de Sofía (no cambian por usuario)
PERSONALITY_CORE = {
    "attachment": 30.0,        # tendencia a establecer vínculos
    "curiosity": 60.0,         # tendencia a preguntar
    "boundary_strength": 70.0, # firmeza en límites
    "sensitivity": 50.0,       # sensibilidad emocional
    "depth": 65.0,             # tendencia a reflexionar
}

# core/session_manager.py
# ============================================================
# SocialBot v0.5.0 — Session Manager
#
# Responsabilidades:
#   - Al ARRANCAR: cargar la última sesión y generar saludo
#   - Al CERRAR: guardar resumen de la sesión actual
# ============================================================

from datetime import datetime
from typing import Optional
from storage.database import Database
from config.sofia_voice import pick
import random


# ============================================================
# SALUDOS CON MEMORIA
# Sofía recuerda temas y días hablando
# ============================================================

SALUDOS = {

    # Usuario nuevo — primera vez
    "nuevo": [
        "¡Holi! Soy Sofía. ¿Cómo estás? 😊",
        "Hola, qué bueno que estás aquí. ¿Cómo te llamas?",
        "¡Oye, hola! Es la primera vez que hablamos, ¿verdad? Cuéntame de ti.",
    ],

    # Usuario conocido — sin temas guardados
    "conocido_sin_temas": [
        "¡Hola! ¿Cómo estás hoy?",
        "Oye, hola. ¿Qué tal tu día?",
        "Holi, ¿cómo vas?",
        "¡Oye! ¿Todo bien por ahí?",
    ],

    # Usuario conocido — con temas guardados
    # {topic} se reemplaza con el tema más relevante
    "conocido_con_tema": [
        "¡Hola! Oye, la otra vez mencionaste {topic}. ¿Cómo va eso?",
        "Holi 😊 Oye, ¿qué pasó con {topic}?",
        "¡Oye! ¿Cómo te fue con {topic}?",
        "Hola, ¿sigues con lo de {topic}?",
    ],

    # Usuario que lleva varios días
    # {days} se reemplaza con el número de días
    "dias_hablando": [
        "¡Oye! Ya llevamos {days} días hablando, jeje.",
        "Hola 😊 ¿Sabías que ya llevamos {days} días? Qué padre.",
        "Holi. {days} días ya, ¿cómo estás hoy?",
    ],
}


class SessionManager:
    """
    Maneja el inicio y cierre de sesión de Sofía.
    """

    def __init__(self, db: Database):
        self.db = db

    # --------------------------------------------------------
    # AL ARRANCAR — generar saludo con memoria
    # --------------------------------------------------------

    def get_greeting(self, user_id: str) -> str:
        """
        Genera el saludo inicial según el historial del usuario.
        Prioridad:
          1. Días hablando (si son ≥ 3)
          2. Tema relevante de la última sesión
          3. Usuario conocido sin temas
          4. Usuario nuevo
        """
        session = self.db.load_last_session(user_id)

        if not session:
            return pick(SALUDOS["nuevo"])

        days = self._days_since(session["date"])
        session_count = session.get("session_count", 1)
        topics = session.get("topics", [])
        facts  = session.get("important_facts", {})

        # 1. Días hablando (≥ 3 sesiones)
        if session_count >= 3:
            frase = pick(SALUDOS["dias_hablando"])
            return frase.format(days=session_count)

        # 2. Tema relevante
        top_topic = self._pick_top_topic(topics, facts)
        if top_topic:
            frase = pick(SALUDOS["conocido_con_tema"])
            return frase.format(topic=top_topic)

        # 3. Conocido sin temas
        return pick(SALUDOS["conocido_sin_temas"])

    # --------------------------------------------------------
    # AL CERRAR — guardar resumen de sesión
    # --------------------------------------------------------

    def save_session(self, user_id: str, profile) -> None:
        """
        Guarda el resumen de la sesión actual.
        Llama esto cuando el usuario escribe 'salir' o el bot se cierra.
        """
        # Incrementar contador de sesiones
        last = self.db.load_last_session(user_id)
        session_count = (last["session_count"] + 1) if last else 1

        self.db.save_session(
            user_id=user_id,
            topics=profile.topics,
            important_facts=profile.important_facts,
            session_count=session_count
        )

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------

    def _days_since(self, date: datetime) -> int:
        """Días desde la última sesión."""
        delta = datetime.now() - date
        return max(0, delta.days)

    def _pick_top_topic(self, topics: list, facts: dict) -> Optional[str]:
        """
        Elige el tema más relevante para mencionar.
        Prioriza hechos con peso alto, luego topics.
        Filtra palabras genéricas que no aportan contexto.
        """
        stopwords = {
            "hola", "bien", "mal", "nada", "algo", "todo",
            "eso", "esto", "aqui", "ahi", "igual", "bueno"
        }

        # Primero buscar en important_facts (más ricos en contexto)
        if facts:
            # Ordenar por peso descendente
            sorted_facts = sorted(facts.items(), key=lambda x: x[1], reverse=True)
            for fact, weight in sorted_facts:
                if weight >= 2.0:
                    # Limpiar el hecho para que suene natural
                    # "le gusta el fútbol" → "el fútbol"
                    clean = self._clean_fact(fact)
                    if clean:
                        return clean

        # Luego topics
        for topic in topics:
            if topic.lower() not in stopwords and len(topic) > 3:
                return topic

        return None

    def _clean_fact(self, fact: str) -> str:
        """
        Convierte un hecho guardado en algo natural para mencionar.
        'le gusta futbol' → 'el fútbol'
        'estudia medicina' → 'la medicina'
        'soy estudiante' → None (demasiado genérico)
        """
        skip_patterns = ["soy ", "tiene ", "es "]
        fact_lower = fact.lower()

        for pattern in skip_patterns:
            if fact_lower.startswith(pattern):
                return ""

        # "le gusta X" → "X"
        if "gusta" in fact_lower:
            parts = fact_lower.split("gusta")
            if len(parts) > 1:
                topic = parts[1].strip()
                return topic if len(topic) > 2 else ""

        # "estudia X" → "X"
        if "estudia" in fact_lower:
            parts = fact_lower.split("estudia")
            if len(parts) > 1:
                return parts[1].strip()

        # "trabaja en X" → "X"
        if "trabaja" in fact_lower:
            parts = fact_lower.split("en")
            if len(parts) > 1:
                return parts[-1].strip()

        return fact


import re
from datetime import datetime
from typing import Optional, List, Dict

from models.user_profile import UserProfile
from models.interaction import Interaction
from storage.database import Database
from utils.text_analyzer import TextAnalyzer
from utils.logger import logger
from config import settings
from core.personality_core import PERSONALITY_CORE


class UserProfileManager:
    """
    Gestiona perfiles con:
    - Memoria ponderada con decaimiento
    - Evolución de personalidad
    - Sistema de daño relacional persistente
    """

    def __init__(self, db: Database):
        self.db = db
        self.analyzer = TextAnalyzer()
        self.cache: Dict[str, UserProfile] = {}

        self.fact_patterns = [
            (re.compile(r'\b(?:soy|soy un|soy una)\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,4})\b', re.IGNORECASE), "soy {0}"),
            (re.compile(r'\b(?:estudio|estoy estudiando)\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,4})\b', re.IGNORECASE), "estudia {0}"),
            (re.compile(r'\b(?:trabajo en|trabajo de)\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,4})\b', re.IGNORECASE), "trabaja en {0}"),
            (re.compile(r'\b(?:me gusta|me encanta)\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,4})\b', re.IGNORECASE), "le gusta {0}"),
            (re.compile(r'\b(?:tengo un|tengo una)\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,4})\b', re.IGNORECASE), "tiene {0}"),
        ]

        self.stopwords = {
            "muy", "bastante", "poco", "algo",
            "un", "una", "unos", "unas",
            "el", "la", "los", "las"
        }

    # ------------------------------------------------------------
    # CARGA / CREACIÓN
    # ------------------------------------------------------------

    async def get_or_create_profile(self, user_id: str) -> UserProfile:
        if user_id in self.cache:
            return self.cache[user_id]

        profile = self.db.load_user_profile(user_id)

        if not profile:
            profile = UserProfile(
                user_id=user_id,
                first_seen=datetime.now(),
                last_seen=datetime.now()
            )
            self.db.save_user_profile(profile)
            logger.info(f"Nuevo perfil creado para {user_id}")

        self.cache[user_id] = profile
        return profile

    # ------------------------------------------------------------
    # ACTUALIZACIÓN PRINCIPAL
    # ------------------------------------------------------------

    async def update_profile_from_interaction(
        self,
        profile: UserProfile,
        interaction: Interaction
    ):
        """
        Actualiza:
        - Hechos (con decaimiento)
        - Rasgos dinámicos
        - Daño relacional
        """

        # 1️⃣ Decaimiento de hechos
        self._apply_fact_decay(profile, interaction.timestamp)

        # 2️⃣ Contadores
        profile.interaction_count += 1
        profile.last_seen = interaction.timestamp
        if not profile.first_seen:
            profile.first_seen = interaction.timestamp

        # 3️⃣ Estilo comunicación
        style = self._detect_communication_style(interaction.message)
        if style:
            profile.communication_style = style

        # 4️⃣ Temas
        keywords = self.analyzer.extract_keywords(interaction.message, max_words=3)
        current_topics = set(profile.topics)
        current_topics.update(keywords)
        profile.topics = list(current_topics)[:10]

        # 5️⃣ Hechos importantes
        detected_facts = self._extract_facts(interaction.message)
        for fact in detected_facts:
            increment = 1.0
            if interaction.sentiment is not None and abs(interaction.sentiment) > 0.7:
                increment += 0.5

            profile.important_facts[fact] = (
                profile.important_facts.get(fact, 0.0) + increment
            )

        if len(profile.important_facts) > 50:
            sorted_facts = sorted(
                profile.important_facts.items(),
                key=lambda x: x[1],
                reverse=True
            )
            profile.important_facts = dict(sorted_facts[:50])

        # ------------------------------------------------------------
        # 🆕 SISTEMA DE DAÑO RELACIONAL (v0.3.4)
        # ------------------------------------------------------------

        if interaction.sentiment is not None:

            # 🔴 Incremento por negatividad
            if interaction.sentiment < -0.3:
                damage_increment = abs(interaction.sentiment) * 2
                profile.relationship_damage += damage_increment

            # 🟢 Reparación emocional (dependiente de la confianza actual)
            repair_mult = self.analyzer.get_repair_multiplier(interaction.message)
            if repair_mult > 1.0 and interaction.sentiment >= 0:
                trust = profile.emotional_state.trust

                # Factor según confianza actual
                if trust > 70:
                    trust_factor = 1.2
                elif trust < 40:
                    trust_factor = 0.5
                else:
                    trust_factor = 1.0

                reduction = repair_mult * 1.5 * trust_factor

                profile.relationship_damage = max(
                    0.0,
                    profile.relationship_damage - reduction
                )

        # ------------------------------------------------------------
        # 🆕 EVOLUCIÓN DE PERSONALIDAD
        # ------------------------------------------------------------

        if interaction.sentiment is not None:

            # Muy positivo → attachment crece
            if interaction.sentiment > 0.5:
                profile.personality_offsets["attachment"] += 0.5

            # Muy negativo → boundaries suben
            elif interaction.sentiment < -0.5:
                profile.personality_offsets["boundary_strength"] += 0.8
                profile.personality_offsets["attachment"] -= 0.5

        # Clamp offsets
        for k in profile.personality_offsets:
            profile.personality_offsets[k] = max(
                -30.0,
                min(30.0, profile.personality_offsets[k])
            )

        # Guardar
        self.db.save_user_profile(profile)
        self.cache[profile.user_id] = profile

    # ------------------------------------------------------------
    # DECAY
    # ------------------------------------------------------------

    def _apply_fact_decay(self, profile: UserProfile, current_time: datetime):
        if not profile.last_seen:
            return

        days_passed = max(
            0,
            (current_time - profile.last_seen).total_seconds() / 86400
        )

        if days_passed == 0:
            return

        decay_factor = settings.FACT_DECAY_PER_DAY ** days_passed

        for fact in list(profile.important_facts.keys()):
            new_weight = profile.important_facts[fact] * decay_factor

            if new_weight < settings.FACT_MIN_WEIGHT:
                del profile.important_facts[fact]
            else:
                profile.important_facts[fact] = new_weight

    # ------------------------------------------------------------
    # EXTRACCIÓN DE HECHOS
    # ------------------------------------------------------------

    def _extract_facts(self, message: str) -> List[str]:
        detected = []

        for pattern, template in self.fact_patterns:
            matches = pattern.findall(message)

            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]

                fact_text = match.strip().lower()

                words = fact_text.split()
                filtered_words = [w for w in words if w not in self.stopwords]

                if not filtered_words:
                    continue

                fact_text = " ".join(filtered_words[:5])
                fact = template.format(fact_text)

                detected.append(fact)

        return detected

    # ------------------------------------------------------------
    # ESTILO
    # ------------------------------------------------------------

    def _detect_communication_style(self, message: str) -> Optional[str]:
        msg = message.lower()

        technical_words = {
            "código", "función", "variable", "bug",
            "python", "javascript", "api",
            "servidor", "base de datos"
        }

        if any(w in msg for w in technical_words):
            return "technical"

        humor = {"jaja", "jeje", "lol", "😂", "😆"}
        if any(w in msg for w in humor):
            return "humorous"

        aggressive = {"idiota", "estúpido", "imbécil", "tonto", "😡"}
        if any(w in msg for w in aggressive):
            return "aggressive"

        return None

    # ------------------------------------------------------------
    # MODIFICADORES DE COMPORTAMIENTO
    # ------------------------------------------------------------

    def get_behavior_modifiers(self, profile: UserProfile) -> dict:

        effective_traits = {}
        for k, base in PERSONALITY_CORE.items():
            offset = profile.personality_offsets.get(k, 0.0)
            effective_traits[k] = max(
                0.0,
                min(100.0, base + offset)
            )

        top_facts = dict(sorted(
            profile.important_facts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5])

        modifiers = {
            "tone": profile.communication_style,
            "empathy_bonus": 0.0,
            "hostility_threshold": 20.0,
            "patience": 1.0,
            "ignore_threshold_adjust": 0.0,
            "effective_traits": effective_traits,
            "important_facts": top_facts
        }

        # ------------------------------------------------------------
        # Historial + confianza
        # ------------------------------------------------------------

        if profile.interaction_count > 10 and profile.emotional_state.trust > 70:
            modifiers["empathy_bonus"] += 0.2
            modifiers["hostility_threshold"] = 10.0

        if profile.emotional_state.trust < 30:
            modifiers["empathy_bonus"] -= 0.1
            modifiers["hostility_threshold"] = 30.0

        # ------------------------------------------------------------
        # 🆕 Daño relacional
        # ------------------------------------------------------------

        damage = profile.relationship_damage

        if damage > 5:
            modifiers["hostility_threshold"] = 25.0
            modifiers["empathy_bonus"] -= 0.2
            modifiers["ignore_threshold_adjust"] = 0.2

        elif damage > 2:
            modifiers["hostility_threshold"] = 22.0
            modifiers["empathy_bonus"] -= 0.1
            modifiers["ignore_threshold_adjust"] = 0.1

        # ------------------------------------------------------------
        # Rasgos efectivos
        # ------------------------------------------------------------

        boundary = effective_traits.get("boundary_strength", 70)
        sensitivity = effective_traits.get("sensitivity", 50)
        depth = effective_traits.get("depth", 65)

        if boundary > 60:
            modifiers["ignore_threshold_adjust"] = 0.1
        elif boundary < 40:
            modifiers["ignore_threshold_adjust"] = -0.1

        modifiers["empathy_bonus"] += (sensitivity - 50) / 500
        modifiers["patience"] += (depth - 50) / 100

        return modifiers



        # models/interaction.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Interaction:
    """Registro de una interacción con un usuario"""
    user_id: str
    message: str
    sentiment: float  # -1 a 1
    response: str
    timestamp: datetime
    emotion_before: str
    emotion_after: str

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "message": self.message,
            "sentiment": self.sentiment,
            "response": self.response,
            "timestamp": self.timestamp.isoformat(),
            "emotion_before": self.emotion_before,
            "emotion_after": self.emotion_after
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            user_id=data["user_id"],
            message=data["message"],
            sentiment=data["sentiment"],
            response=data["response"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            emotion_before=data["emotion_before"],
            emotion_after=data["emotion_after"]
        )

# models/state.py
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class Emotion(Enum):
    HAPPY = "happy"
    NEUTRAL = "neutral"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"

@dataclass
class EmotionalState:
    """Estado emocional actual del bot"""
    primary_emotion: Emotion = Emotion.NEUTRAL
    energy: float = 100.0      # 0-100, qué tan activo/enérgico
    trust: float = 100.0       # 0-100, confianza general en usuarios
    last_updated: Optional[float] = None  # timestamp

    def to_dict(self) -> dict:
        return {
            "emotion": self.primary_emotion.value,
            "energy": self.energy,
            "trust": self.trust,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            primary_emotion=Emotion(data.get("emotion", "neutral")),
            energy=data.get("energy", 50.0),
            trust=data.get("trust", 50.0),
            last_updated=data.get("last_updated")
        )



        from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
from models.state import EmotionalState
from core.personality_core import PERSONALITY_CORE

RELATIONAL_TRAIT_KEYS = list(PERSONALITY_CORE.keys())

@dataclass
class UserProfile:
    user_id: str
    emotional_state: EmotionalState = field(default_factory=EmotionalState)
    interaction_count: int = 0
    communication_style: str = "neutral"
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    topics: List[str] = field(default_factory=list)
    
    # 🔄 OFFSETS: desviación respecto al núcleo
    personality_offsets: Dict[str, float] = field(
        default_factory=lambda: {k: 0.0 for k in RELATIONAL_TRAIT_KEYS}
    )
    
    # 🧠 Hechos importantes (memoria selectiva)
    important_facts: Dict[str, float] = field(default_factory=dict)

    # ⚠️ NUEVO: Daño relacional acumulado (0 = sin daño, >0 = daño)
    relationship_damage: float = 0.0

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "emotional_state": self.emotional_state.to_dict() if self.emotional_state else None,
            "interaction_count": self.interaction_count,
            "communication_style": self.communication_style,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "topics": self.topics,
            "personality_offsets": self.personality_offsets,
            "important_facts": self.important_facts,
            "relationship_damage": self.relationship_damage   # ← nuevo campo
        }

    @classmethod
    def from_dict(cls, data: dict):
        emotional_state_data = data.get("emotional_state")
        emotional_state = EmotionalState.from_dict(emotional_state_data) if emotional_state_data else EmotionalState()

        topics = data.get("topics", [])
        if isinstance(topics, str):
            topics = [t.strip() for t in topics.split(",") if t.strip()]

        # Migración desde personality_traits si existe
        old_traits = data.get("personality_traits")
        if old_traits is not None:
            offsets = {}
            for k in RELATIONAL_TRAIT_KEYS:
                old_val = old_traits.get(k, PERSONALITY_CORE[k])
                offsets[k] = old_val - PERSONALITY_CORE[k]
        else:
            offsets = data.get("personality_offsets", {})
            offsets = {k: offsets.get(k, 0.0) for k in RELATIONAL_TRAIT_KEYS}

        important_facts = data.get("important_facts") or {}
        if not isinstance(important_facts, dict):
            important_facts = {}

        # Cargar relationship_damage (si no existe, inicializar a 0)
        relationship_damage = data.get("relationship_damage", 0.0)

        return cls(
            user_id=data["user_id"],
            emotional_state=emotional_state,
            interaction_count=data.get("interaction_count", 0),
            communication_style=data.get("communication_style", "neutral"),
            first_seen=datetime.fromisoformat(data["first_seen"]) if data.get("first_seen") else None,
            last_seen=datetime.fromisoformat(data["last_seen"]) if data.get("last_seen") else None,
            topics=topics,
            personality_offsets=offsets,
            important_facts=important_facts,
            relationship_damage=relationship_damage
        )

        # storage/database.py
# ============================================================
# SocialBot v0.5.0 — Memoria Episódica
# Cambios:
#   - Nueva tabla `sessions` para recordar la última sesión
#   - Métodos: save_session, load_last_session
#   - Todo lo demás igual, sin romper nada existente
# ============================================================

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from models.state import Emotion, EmotionalState
from models.interaction import Interaction
from models.user_profile import UserProfile
from utils.logger import logger


class Database:
    def __init__(self, db_path: str = "data/bot_data.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    # --------------------------------------------------
    # INIT DATABASE
    # --------------------------------------------------

    def _init_db(self):
        Path("data").mkdir(exist_ok=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Interactions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    message TEXT,
                    sentiment REAL,
                    response TEXT,
                    timestamp TEXT,
                    emotion_before TEXT,
                    emotion_after TEXT
                )
            """)

            # Emotional State Global
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emotional_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    emotion TEXT,
                    energy REAL,
                    trust REAL,
                    last_updated TEXT
                )
            """)

            # User Profiles
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    emotional_state TEXT,
                    interaction_count INTEGER DEFAULT 0,
                    communication_style TEXT DEFAULT 'neutral',
                    first_seen TEXT,
                    last_seen TEXT,
                    topics TEXT,
                    personality_traits TEXT,
                    important_facts TEXT,
                    relationship_damage REAL DEFAULT 0.0
                )
            """)

            # -------------------------
            # 🆕 v0.5.0 — Sessions
            # Guarda un resumen de la última sesión por usuario.
            # Solo se mantiene 1 registro por user_id (INSERT OR REPLACE).
            # -------------------------
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    session_count INTEGER DEFAULT 1,
                    topics TEXT,
                    important_facts TEXT
                )
            """)

            conn.commit()

            # Migraciones para DBs existentes
            for migration in [
                "ALTER TABLE user_profiles ADD COLUMN relationship_damage REAL DEFAULT 0.0",
            ]:
                try:
                    cursor.execute(migration)
                    conn.commit()
                except sqlite3.OperationalError:
                    pass

            # Estado emocional inicial
            cursor.execute("SELECT * FROM emotional_state WHERE id = 1")
            if not cursor.fetchone():
                initial = EmotionalState()
                cursor.execute("""
                    INSERT INTO emotional_state (id, emotion, energy, trust, last_updated)
                    VALUES (1, ?, ?, ?, ?)
                """, (initial.primary_emotion.value, initial.energy, initial.trust, None))
                conn.commit()

    # --------------------------------------------------
    # INTERACTIONS
    # --------------------------------------------------

    def save_interaction(self, interaction: Interaction) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interactions
                (user_id, message, sentiment, response, timestamp,
                 emotion_before, emotion_after)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                interaction.user_id,
                interaction.message,
                interaction.sentiment,
                interaction.response,
                interaction.timestamp.isoformat(),
                interaction.emotion_before,
                interaction.emotion_after
            ))
            conn.commit()
            return cursor.lastrowid

    def get_user_interactions(self, user_id: str, limit: int = 10) -> List[Interaction]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, message, sentiment, response, timestamp,
                       emotion_before, emotion_after
                FROM interactions
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))

            rows = cursor.fetchall()
            return [
                Interaction(
                    user_id=row[0], message=row[1], sentiment=row[2],
                    response=row[3],
                    timestamp=datetime.fromisoformat(row[4]),
                    emotion_before=row[5], emotion_after=row[6]
                )
                for row in rows
            ]

    # --------------------------------------------------
    # USER PROFILES
    # --------------------------------------------------

    def save_user_profile(self, profile: UserProfile):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            emotional_state_json = (
                json.dumps(profile.emotional_state.to_dict())
                if profile.emotional_state else None
            )
            topics_str   = ",".join(profile.topics) if profile.topics else None
            traits_json  = json.dumps(profile.personality_offsets) if profile.personality_offsets else None
            facts_json   = json.dumps(profile.important_facts) if profile.important_facts else None

            cursor.execute("""
                INSERT OR REPLACE INTO user_profiles
                (user_id, emotional_state, interaction_count,
                 communication_style, first_seen, last_seen,
                 topics, personality_traits, important_facts, relationship_damage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.user_id,
                emotional_state_json,
                profile.interaction_count,
                profile.communication_style,
                profile.first_seen.isoformat() if profile.first_seen else None,
                profile.last_seen.isoformat() if profile.last_seen else None,
                topics_str,
                traits_json,
                facts_json,
                profile.relationship_damage
            ))
            conn.commit()

    def load_user_profile(self, user_id: str) -> Optional[UserProfile]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, emotional_state, interaction_count,
                       communication_style, first_seen, last_seen,
                       topics, personality_traits, important_facts, relationship_damage
                FROM user_profiles WHERE user_id = ?
            """, (user_id,))

            row = cursor.fetchone()
            if not row:
                return None

            emotional_state_data = json.loads(row[1]) if row[1] else None
            topics               = row[6].split(",") if row[6] else []
            traits_data          = json.loads(row[7]) if row[7] else {}
            facts_data           = json.loads(row[8]) if row[8] else {}
            relationship_damage  = row[9] if row[9] is not None else 0.0

            data = {
                "user_id": row[0],
                "emotional_state": emotional_state_data,
                "interaction_count": row[2],
                "communication_style": row[3],
                "first_seen": row[4],
                "last_seen": row[5],
                "topics": topics,
                "personality_traits": traits_data,
                "important_facts": facts_data,
                "relationship_damage": relationship_damage
            }
            return UserProfile.from_dict(data)

    # --------------------------------------------------
    # STATS
    # --------------------------------------------------

    def get_average_sentiment_for_user(self, user_id: str) -> float:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT AVG(sentiment) FROM interactions WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()[0]
            return result if result is not None else 0.0

    # --------------------------------------------------
    # 🆕 v0.5.0 — SESSIONS
    # --------------------------------------------------

    def save_session(
        self,
        user_id: str,
        topics: List[str],
        important_facts: dict,
        session_count: int
    ):
        """
        Guarda (o actualiza) el resumen de la sesión actual.
        Solo existe 1 registro por usuario — siempre es la última sesión.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sessions
                (user_id, date, session_count, topics, important_facts)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                datetime.now().isoformat(),
                session_count,
                ",".join(topics[:10]) if topics else "",
                json.dumps(important_facts) if important_facts else "{}"
            ))
            conn.commit()

    def load_last_session(self, user_id: str) -> Optional[dict]:
        """
        Carga el resumen de la última sesión del usuario.
        Devuelve None si no existe (usuario nuevo).
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, session_count, topics, important_facts
                FROM sessions WHERE user_id = ?
            """, (user_id,))

            row = cursor.fetchone()
            if not row:
                return None

            topics = [t.strip() for t in row[2].split(",") if t.strip()] if row[2] else []
            facts  = json.loads(row[3]) if row[3] else {}

            return {
                "date":          datetime.fromisoformat(row[0]),
                "session_count": row[1],
                "topics":        topics,
                "important_facts": facts
            }


            # utils/aggression_detector.py
# ============================================================
# SocialBot v0.6.0 — Detector de Agresión Contextual
# ============================================================

import unicodedata


INSULT_LEVELS = {
    "leve": [
        "wey", "guey", "tonto", "tonta", "idiota", "imbecil",
        "mensa", "menso", "tarado", "tarada", "baboso", "babosa",
        "naco", "naca", "pesado", "pesada", "estupido", "estupida",
        "callate", "calla",
    ],
    "medio": [
        "eres una basura", "eres una mierda", "te odio",
        "no sirves", "eres inutil", "que asco",
        "eres horrible", "eres un fracaso", "me haces perder el tiempo",
        "eres lo peor", "a nadie le importas", "eres patetica",
        "eres patetico", "maldito bot", "eres una porqueria",
    ],
    "alto": [
        "vete al diablo", "vete a la chingada", "a la verga",
        "chinga tu madre", "ojete", "te voy a bloquear",
        "eres una maldita", "eres un maldito", "ojala te mueras",
        "cierra la boca", "callate la boca",
    ],
}

IMPACT_WEIGHTS = {
    "leve":  {"energy": -5.0,  "trust": -3.0,  "damage": 0.5},
    "medio": {"energy": -10.0, "trust": -7.0,  "damage": 1.5},
    "alto":  {"energy": -18.0, "trust": -12.0, "damage": 3.0},
}

# Si el mensaje tiene estos tokens Y trust > 75 → broma, impacto reducido
JOKE_INDICATORS = {"jaja", "jeje", "jajaja", "jejeje", "lol", "xd", ":v", "😂", "🤣"}


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFD", text)
    return nfkd.encode("ascii", "ignore").decode("utf-8").lower()


class AggressionDetector:
    """
    Detecta insultos con 3 niveles (leve / medio / alto).
    Si parece broma Y trust > 75, reduce el impacto a 40%.
    """

    def detect(self, message: str, trust: float = 50.0) -> dict:
        """
        Retorna:
          {
            "detected":  bool,
            "level":     str | None,   # "leve", "medio", "alto"
            "impact":    dict | None,  # deltas: energy, trust, damage
            "is_joke":   bool,
          }
        """
        msg_norm  = _normalize(message)
        msg_lower = message.lower()
        is_joke   = any(ind in msg_lower for ind in JOKE_INDICATORS)

        for level in ("alto", "medio", "leve"):
            for phrase in INSULT_LEVELS[level]:
                if phrase in msg_norm:
                    impact = IMPACT_WEIGHTS[level].copy()
                    reported_level = level

                    # Broma entre amigos → impacto reducido
                    if is_joke and trust > 75:
                        impact = {k: v * 0.4 for k, v in impact.items()}
                        reported_level = "leve"

                    return {
                        "detected": True,
                        "level":    reported_level,
                        "impact":   impact,
                        "is_joke":  is_joke,
                    }

        return {"detected": False, "level": None, "impact": None, "is_joke": False}



# utils/logger.py
import logging
import sys
from pathlib import Path

def setup_logger(name: str = "social_bot", level=logging.INFO):
    """Configura y retorna un logger"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Formato
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para archivo (opcional)
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "bot.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# Crear una instancia global para usar en toda la app
logger = setup_logger()




# utils/text_analyzer.py
# ============================================================
# SocialBot v0.3.6 — Fix: normalización de acentos
# Cambios:
#   - Nuevo método _normalize() para quitar tildes
#   - extract_keywords y analyze_sentiment usan _normalize()
#   - Así "fútbol" y "futbol" se tratan como la misma palabra
# ============================================================

import re
import unicodedata
from typing import List
from config import settings


class TextAnalyzer:
    """Analizador de texto simple basado en palabras clave"""

    def __init__(self):
        self.positive_words = {
            "gracias", "genial", "buen", "bien", "excelente", "perfecto",
            "amor", "feliz", "alegre", "maravilloso",
            "te quiero", "te amo", "helpful", "thanks", "good", "great",
            "amo", "quiero", "adoro"
        }

        self.negative_words = {
            "mal", "peor", "odio", "estupido", "tonto", "feo",
            "horrible", "terrible", "asco",
            "imbecil", "idiota", "hate", "bad", "stupid",
            "odias", "detesto", "aborrezco"
        }

        self.intensifiers = {
            "muy", "mucho", "bastante", "demasiado",
            "super", "really", "very"
        }

        self.apology_phrases = [
            "perdon", "lo siento", "disculpa", "perdona",
            "sorry", "me equivoque", "fue mi culpa", "no quise"
        ]

        self.affection_phrases = [
            "te quiero", "te amo", "aprecio", "gracias por",
            "me importas", "eres importante", "te adoro"
        ]

    # ---------------------------
    # NORMALIZACIÓN (Fix v0.3.6)
    # ---------------------------

    def _normalize(self, text: str) -> str:
        """
        Quita tildes y convierte a minúsculas.
        'fútbol' → 'futbol', 'perdón' → 'perdon'
        """
        nfkd = unicodedata.normalize('NFD', text)
        without_accents = nfkd.encode('ascii', 'ignore').decode('utf-8')
        return without_accents.lower()

    # ---------------------------
    # SENTIMIENTO BASE
    # ---------------------------

    def analyze_sentiment(self, text: str) -> float:
        """
        Retorna un valor entre -1 (muy negativo) y 1 (muy positivo).
        Ahora normaliza acentos antes de comparar.
        """
        text_normalized = self._normalize(text)
        negation_words = {"no", "nunca", "jamas", "not", "never"}
        words = text_normalized.split()

        score = 0.0
        found_words = 0
        negate = False

        for i, word in enumerate(words):
            word_clean = re.sub(r'[^\w]', '', word)
            if not word_clean:
                continue

            if word_clean in negation_words:
                negate = True
                continue

            multiplier = 1.0
            if i > 0:
                prev_word = re.sub(r'[^\w]', '', words[i - 1])
                if prev_word in self.intensifiers:
                    multiplier = 1.5

            if word_clean in self.positive_words:
                score += (1.0 * multiplier) * (-1 if negate else 1)
                found_words += 1
                negate = False

            elif word_clean in self.negative_words:
                score += (-1.0 * multiplier) * (-1 if negate else 1)
                found_words += 1
                negate = False

        if found_words == 0:
            return 0.0

        return max(-1.0, min(1.0, score / found_words))

    # ---------------------------
    # PALABRAS CLAVE
    # ---------------------------

    def extract_keywords(self, text: str, max_words: int = 5) -> List[str]:
        """
        Extrae palabras clave normalizadas (sin tildes).
        Así 'fútbol' y 'futbol' producen la misma keyword: 'futbol'
        """
        normalized = self._normalize(text)
        words = re.findall(r'\b\w+\b', normalized)

        stopwords = {
            "de", "la", "que", "el", "en", "y", "a", "los",
            "del", "se", "las", "por", "un", "para", "con",
            "no", "una", "su", "al", "lo", "como", "mas",
            "pero", "sus", "le", "ya", "o", "fue", "este",
            "si", "mi", "hoy", "fue"
        }

        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        return keywords[:max_words]

    # ---------------------------
    # REPARACIÓN EMOCIONAL
    # ---------------------------

    def is_apology(self, text: str) -> bool:
        text_normalized = self._normalize(text)
        return any(phrase in text_normalized for phrase in self.apology_phrases)

    def is_affection(self, text: str) -> bool:
        text_normalized = self._normalize(text)
        return any(phrase in text_normalized for phrase in self.affection_phrases)

    def get_repair_multiplier(self, text: str) -> float:
        multiplier = 1.0
        if self.is_apology(text):
            multiplier *= settings.APOLOGY_MULTIPLIER
        if self.is_affection(text):
            multiplier *= settings.AFFECTION_MULTIPLIER
        return multiplier


        # discord_bot.py
# ============================================================
# SocialBot v0.6.1 — Discord
# Cambios v0.6.1:
#   - Embed de estado emocional debajo de cada respuesta
#   - Muestra: emoción, energía, confianza, daño, agresión sesión
# ============================================================

import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.logger import logger
from storage.database import Database
from core.memory import Memory
from core.emotion_engine import EmotionEngine
from core.decision_engine import DecisionEngine
from core.user_profile_manager import UserProfileManager
from core.session_manager import SessionManager
from config import settings

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ============================================================
# CONFIGURACIÓN DEL BOT
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ============================================================
# INSTANCIAS GLOBALES
# ============================================================

db              = Database(str(settings.DATABASE_PATH))
memory          = Memory(db)
profile_manager = UserProfileManager(db)
emotion_engine  = EmotionEngine()
decision        = DecisionEngine()
session_manager = SessionManager(db)


# ============================================================
# HELPERS — Embed de estado emocional
# ============================================================

EMOTION_COLORS = {
    "happy":   0x57F287,   # verde
    "neutral": 0x5865F2,   # azul Discord
    "sad":     0x4E5058,   # gris oscuro
    "angry":   0xED4245,   # rojo
    "fearful": 0xFEE75C,   # amarillo
}

EMOTION_EMOJI = {
    "happy":   "😊",
    "neutral": "😐",
    "sad":     "😔",
    "angry":   "😠",
    "fearful": "😨",
}

def _energy_bar(value: float, length: int = 10) -> str:
    filled = round(value / 100 * length)
    return "█" * filled + "░" * (length - filled)

def build_state_embed(profile, decision_engine, user_id: str) -> discord.Embed:
    """Construye el embed de estado emocional de Sofía."""
    estado   = profile.emotional_state
    emo_val  = estado.primary_emotion.value
    color    = EMOTION_COLORS.get(emo_val, 0x5865F2)
    emoji    = EMOTION_EMOJI.get(emo_val, "😐")

    agg_count  = decision_engine.aggression_count.get(user_id, 0)
    rec_needed = decision_engine.recovery_needed.get(user_id, 0)

    embed = discord.Embed(color=color)
    embed.set_author(name="Estado emocional de Sofía")

    embed.add_field(
        name="Emoción",
        value=f"{emoji} `{emo_val}`",
        inline=True
    )
    embed.add_field(
        name="Energía",
        value=f"`{estado.energy:5.1f}` {_energy_bar(estado.energy)}",
        inline=True
    )
    embed.add_field(
        name="Confianza",
        value=f"`{estado.trust:5.1f}` {_energy_bar(estado.trust)}",
        inline=True
    )
    embed.add_field(
        name="Daño relacional",
        value=f"`{profile.relationship_damage:.2f}`",
        inline=True
    )

    # Mostrar estado de agresión/recuperación si hay algo activo
    if agg_count > 0 or rec_needed > 0:
        status_parts = []
        if agg_count > 0:
            status_parts.append(f"⚠️ Insultos sesión: `{agg_count}`")
        if rec_needed > 0:
            status_parts.append(f"🔄 Recuperación: `{rec_needed}` msgs pendientes")
        embed.add_field(
            name="Estado de sesión",
            value="\n".join(status_parts),
            inline=False
        )

    return embed


# ============================================================
# EVENTOS
# ============================================================

@bot.event
async def on_ready():
    logger.info(f"Sofía conectada como {bot.user}")
    print(f"\n✅ Sofía está en línea como {bot.user}\n")


@bot.event
async def on_member_join(member):
    channel = member.guild.system_channel
    if channel:
        greeting = session_manager.get_greeting(str(member.id))
        await channel.send(f"{member.mention} {greeting}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.author.bot:
        return

    is_dm      = isinstance(message.channel, discord.DMChannel)
    is_mention = bot.user in message.mentions

    if not is_dm and not is_mention:
        return

    content = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not content:
        content = "hola"

    user_id = str(message.author.id)

    async with message.channel.typing():
        response, profile = await process_message(user_id, content)

    # Respuesta de texto
    await message.reply(response)

    # Embed de estado emocional debajo
    embed = build_state_embed(profile, decision, user_id)
    await message.channel.send(embed=embed)

    await bot.process_commands(message)


# ============================================================
# PROCESAR MENSAJE
# ============================================================

async def process_message(user_id: str, message: str):
    """Retorna (response, profile) para poder construir el embed."""
    logger.info(f"Mensaje de {user_id}: {message}")

    profile   = await profile_manager.get_or_create_profile(user_id)
    modifiers = profile_manager.get_behavior_modifiers(profile)

    decision_result = await decision.decide_response(
        user_id=user_id,
        message=message,
        emotion=profile.emotional_state,
        memory=memory,
        profile_modifiers=modifiers
    )

    interaction       = decision_result["interaction"]
    repair_multiplier = decision.analyzer.get_repair_multiplier(message)

    new_state = await emotion_engine.process_interaction_for_state(
        state=profile.emotional_state,
        interaction=interaction,
        memory=memory,
        repair_multiplier=repair_multiplier,
        relationship_damage=profile.relationship_damage
    )

    interaction.emotion_after = new_state.primary_emotion.value
    profile.emotional_state   = new_state

    await memory.remember(interaction)
    await profile_manager.update_profile_from_interaction(profile, interaction)

    return decision_result["response"], profile


# ============================================================
# COMANDOS
# ============================================================

@bot.command(name="sofia")
async def sofia_info(ctx):
    await ctx.send(
        f"Holi, soy Sofía 😊\n"
        f"Versión: `{settings.VERSION}`\n"
        f"Creada por: `JesusJM`\n"
        f"Mencióname o escríbeme por DM para hablar."
    )


@bot.command(name="estado")
async def estado_cmd(ctx):
    """!estado — muestra el estado emocional de Sofía contigo"""
    user_id = str(ctx.author.id)
    profile = await profile_manager.get_or_create_profile(user_id)
    embed   = build_state_embed(profile, decision, user_id)
    await ctx.send(embed=embed)


@bot.command(name="reset")
async def reset_cmd(ctx):
    """!reset — resetea los contadores de sesión (solo para testing)"""
    user_id = str(ctx.author.id)
    decision.aggression_count.pop(user_id, None)
    decision.recovery_needed.pop(user_id, None)
    decision.short_streak.pop(user_id, None)
    decision.secrets_revealed.pop(user_id, None)
    await ctx.send("🔄 Contadores de sesión reseteados.")


# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    if not TOKEN:
        print("❌ No encontré el token. Crea un archivo .env con DISCORD_TOKEN=tu_token")
    else:
        bot.run(TOKEN)


# main.py
# ============================================================
# SocialBot v0.5.0 — Memoria Episódica
# Cambios:
#   - Integra SessionManager al arrancar y al cerrar
#   - Sofía saluda según el historial del usuario
#   - Al escribir 'salir' guarda la sesión automáticamente
# ============================================================

import asyncio
from utils.logger import logger
from storage.database import Database
from core.memory import Memory
from core.emotion_engine import EmotionEngine
from core.decision_engine import DecisionEngine
from core.user_profile_manager import UserProfileManager
from core.session_manager import SessionManager
from config import settings


class SocialBot:
    def __init__(self):
        self.db              = Database(str(settings.DATABASE_PATH))
        self.memory          = Memory(self.db)
        self.profile_manager = UserProfileManager(self.db)
        self.emotion_engine  = EmotionEngine()
        self.decision        = DecisionEngine()
        self.session_manager = SessionManager(self.db)   # 🆕
        logger.info("Bot inicializado.")

    async def process_message(self, user_id: str, message: str) -> str:
        logger.info(f"Mensaje de {user_id}: {message}")

        profile   = await self.profile_manager.get_or_create_profile(user_id)
        modifiers = self.profile_manager.get_behavior_modifiers(profile)

        decision = await self.decision.decide_response(
            user_id=user_id,
            message=message,
            emotion=profile.emotional_state,
            memory=self.memory,
            profile_modifiers=modifiers
        )

        interaction      = decision["interaction"]
        repair_multiplier = self.decision.analyzer.get_repair_multiplier(message)

        new_state = await self.emotion_engine.process_interaction_for_state(
            state=profile.emotional_state,
            interaction=interaction,
            memory=self.memory,
            repair_multiplier=repair_multiplier,
            relationship_damage=profile.relationship_damage
        )

        interaction.emotion_after  = new_state.primary_emotion.value
        profile.emotional_state    = new_state

        await self.memory.remember(interaction)
        await self.profile_manager.update_profile_from_interaction(profile, interaction)

        return decision["response"]

    async def run_cli(self):
        print(f"\n--- {settings.BOT_NAME} v{settings.VERSION} ---")
        print("Escribe 'salir' para terminar.\n")

        user_id = "test_user_1"

        # 🆕 Saludo con memoria episódica
        greeting = self.session_manager.get_greeting(user_id)
        print(f"Sofía: {greeting}\n")

        while True:
            user_input = input("Tú: ")
            if user_input.lower() in ["salir", "exit", "quit"]:
                # 🆕 Guardar sesión al cerrar
                profile = await self.profile_manager.get_or_create_profile(user_id)
                self.session_manager.save_session(user_id, profile)
                print("Sofía: ¡Hasta luego! 😊")
                break

            response = await self.process_message(user_id, user_input)
            print(f"Sofía: {response}")

            profile = await self.profile_manager.get_or_create_profile(user_id)
            estado  = profile.emotional_state
            print(f"[{estado.primary_emotion.value} | energía:{estado.energy:.1f} confianza:{estado.trust:.1f} daño:{profile.relationship_damage:.2f}]\n")


async def main():
    bot = SocialBot()
    await bot.run_cli()


if __name__ == "__main__":
    asyncio.run(main())
