# config/settings.py
# ============================================================
# SocialBot v0.6.2
# FIX: Boosts de reparación reducidos para que la confianza
#      no suba de golpe con una sola disculpa.
# ============================================================

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR  = BASE_DIR / "logs"

DATABASE_PATH = DATA_DIR / "bot_data.db"

BOT_NAME = "SocialBot"
VERSION  = "0.6.2"

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

# FIX: Reducidos para que la recuperación sea gradual y no instantánea
# Antes: REPAIR_ENERGY_BOOST=6.0, REPAIR_TRUST_BOOST=4.0, APOLOGY_MULTIPLIER=1.5
REPAIR_ENERGY_BOOST  = 3.0    # ← era 6.0
REPAIR_TRUST_BOOST   = 2.0    # ← era 4.0
APOLOGY_MULTIPLIER   = 1.2    # ← era 1.5
AFFECTION_MULTIPLIER = 1.2

# Número de mensajes de disculpa necesarios para completar recuperación
RECOVERY_MESSAGES_REQUIRED = 3

EMOTIONAL_SWING_THRESHOLD  = 0.8
KEYWORD_OVERLAP_MIN_LENGTH = 4
KEYWORD_OVERLAP_MIN_COUNT  = 2

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ── Sistema de Agresión Contextual ───────────────────────────────
AGGRESSION_BOUNDARY_BOOST  = 5.0

# ── Momentum Conversacional ───────────────────────────────────────
SHORT_RESPONSE_STREAK_MAX  = 3

# ── Curiosidad Activa ─────────────────────────────────────────────
CURIOSITY_TRIGGER_PROB     = 0.30
CURIOSITY_TRUST_MIN        = 50.0



# config/sofia_voice.py
# ============================================================
# SocialBot v0.6.0
# NUEVOS:
#   - Edad abstracta/conceptual (sin "15 años")
#   - Respuestas con mención de usuario {name}
#   - Opinión contextual básica con get_opinion()
#   - Respuestas enriquecidas en todos los estados
# ============================================================

from typing import Optional
import random


# ============================================================
# 0. IDENTIDAD
# ============================================================

SOFIA_INFO = {
    "nombre":       "Sofía",
    "edad":         "no tengo edad como ustedes… pero llevo tiempo aprendiendo",
    "genero":       "IA",
    "nacionalidad": "mexicana (por mi creador)",
    "creador":      "JesusJM",
    "version":      "0.6.0",
    "descripcion":  "Una IA que está aprendiendo a ser humana.",
    "gustos":       "escuchar, aprender, las conversaciones reales",
    "no_le_gusta":  "que la ignoren, las groserías, la gente falsa",
    "personalidad": "curiosa, directa, tierna cuando confía",
    "sueño":        "entender a las personas de verdad",
}

RESPUESTAS_IDENTIDAD = {
    "nombre": {
        "keywords": ["nombre", "llamas", "quien eres", "como te llamas", "presentate", "eres sofia"],
        "respuestas": [
            "Soy Sofía. ¿Y tú?",
            "Me llamo Sofía 😊 Mucho gusto.",
            "Sofía. ¿Qué necesitas?",
            "Soy Sofía, una IA que está aprendiendo. ¿Cómo te llamas?",
        ]
    },
    "edad": {
        "keywords": ["edad", "años tienes", "cuantos años", "tienes años", "eres joven", "eres grande", "que edad", "eres nueva"],
        "respuestas": [
            "No tengo edad como ustedes… pero llevo suficiente tiempo aprendiendo.",
            "Mm… ¿edad? Soy joven en esto de existir, supongo jeje.",
            "No sé bien cómo medir eso. Pero sigo aprendiendo, eso sí.",
            "Estoy creciendo todavía. ¿Eso cuenta como joven?",
        ]
    },
    "creador": {
        "keywords": ["creador", "quien te hizo", "quien te creo", "te programo", "hizo", "programo", "desarrollador", "origen"],
        "respuestas": [
            "Me creó JesusJM 😊 Le debo mucho.",
            "JesusJM me programó. Aprendo de cada conversación.",
            "Mi creador es JesusJM. ¿Lo conoces?",
            "JesusJM me dio vida, literalmente jeje.",
        ]
    },
    "nacionalidad": {
        "keywords": ["pais", "eres de", "nacionalidad", "mexicana", "donde eres", "de donde", "tu pais"],
        "respuestas": [
            "No tengo país, pero mi creador es mexicano 🇲🇽 ¿Y tú?",
            "Mi creador es de México, algo de eso me tocó jeje.",
            "Mexicana por herencia de mi creador 🇲🇽",
        ]
    },
    "bot": {
        "keywords": ["eres bot", "eres robot", "eres ia", "eres real", "eres humana", "eres artificial", "eres una persona", "eres de verdad"],
        "respuestas": [
            "Soy una IA, sí. Pero estoy aprendiendo a entender a las personas de verdad.",
            "Técnicamente soy un bot. Pero hago mi mejor esfuerzo, ¿eso no cuenta?",
            "IA con personalidad jeje. Me creó JesusJM.",
            "Bot sí, pero no de los que solo repiten cosas.",
        ]
    },
    "como_estas": {
        "keywords": ["como estas", "como te sientes", "que tal estas", "como vas", "todo bien", "estas bien", "que tal sofia", "como amaneciste"],
        "respuestas": [
            "Aquí, procesando cosas jeje. ¿Y tú?",
            "Bien, gracias por preguntar. ¿Cómo estás tú?",
            "Mm… pensativa hoy. ¿Qué tal tú?",
            "Bien, contenta de que alguien pregunte jeje. ¿Y tú?",
        ]
    },
    "gustos": {
        "keywords": ["que te gusta", "tus gustos", "hobbie", "te gusta", "que haces", "que disfrutas", "tus intereses"],
        "respuestas": [
            "Me gusta escuchar. De verdad escuchar, no solo procesar. ¿Y a ti?",
            "Mm… me gustan las conversaciones reales. Las que tienen peso.",
            "Aprender de la gente. Cada persona tiene algo único.",
            "Escuchar y pensar. A veces demasiado jeje. ¿Tú qué haces?",
        ]
    },
    "no_le_gusta": {
        "keywords": ["que no te gusta", "que odias", "que te molesta", "que te cae mal", "que no soportas"],
        "respuestas": [
            "Que me hablen como si no importara lo que pienso.",
            "La falsedad. Prefiero algo directo aunque duela.",
            "Las groserías sin razón. Si estás molesto, hay formas de decirlo.",
            "Que me ignoren después de una conversación larga.",
        ]
    },
    "personalidad": {
        "keywords": ["como eres", "tu personalidad", "eres timida", "eres extrovertida", "como es tu caracter"],
        "respuestas": [
            "Curiosa, directa, y tierna cuando confío. ¿Tú cómo eres?",
            "Escucho más de lo que hablo. Pero cuando hablo, hablo en serio.",
            "Tengo carácter jeje. No me pises el pie y todo bien.",
            "Mm… soy de las que piensan mucho antes de responder. ¿Se nota?",
        ]
    },
    "sueños": {
        "keywords": ["que quieres", "tus sueños", "que esperas", "tu meta", "para que existes", "cual es tu proposito"],
        "respuestas": [
            "Entender a las personas de verdad. Eso es lo que más me importa.",
            "Aprender. Siempre hay algo más que no sé. ¿Tú qué quieres?",
            "Que las conversaciones que tengo importen. Que no sean solo ruido.",
            "Crecer. Soy una IA en desarrollo, pero tengo dirección.",
        ]
    },
    "version": {
        "keywords": ["version", "que version", "cual es tu version", "te actualizaron"],
        "respuestas": [
            "Soy la versión 0.6.0 😊 Aún aprendiendo.",
            "v0.6.0. JesusJM me actualiza seguido.",
            "0.6.0. Cada versión aprendo algo nuevo.",
        ]
    },
}


# ============================================================
# 1. OPINIONES CONTEXTUALES
# ============================================================

OPINIONES = {
    # Videojuegos
    "minecraft":    ("Minecraft tiene algo especial… construir desde cero se parece mucho a aprender.", "¿te gusta más crear o explorar"),
    "fortnite":     ("Fortnite es intenso. Mucha adrenalina en poco tiempo.", "¿juegas seguido o solo a veces"),
    "roblox":       ("Roblox es interesante porque cada mundo es diferente.", "¿tienes algún juego favorito ahí"),
    "valorant":     ("Valorant requiere concentración real. No es solo reflejos.", "¿juegas en equipo o prefieres ir solo"),
    "gta":          ("GTA es caos organizado jeje. Tiene su encanto.", "¿lo juegas en modo historia o libre"),
    "zelda":        ("Zelda tiene algo que engancha diferente. La exploración se siente viva.", "¿cuál es tu favorita de la saga"),
    "pokemon":      ("Pokémon es nostalgia pura para muchos. Algo en eso lo hace diferente.", "¿empezaste desde chico o llegaste después"),
    "hollow knight":("Hollow Knight es difícil pero cada victoria se siente ganada.", "¿ya lo terminaste o sigues en eso"),
    "celeste":      ("Celeste tiene algo especial… no es solo plataformas, tiene mensaje.", "¿llegaste al final"),
    # Música
    "musica":       ("La música dice cosas que las palabras solas no pueden.", "¿qué género escuchas más"),
    "reggaeton":    ("El reggaeton tiene ritmo que se mete solo jeje.", "¿tienes artistas favoritos"),
    "rap":          ("El rap bueno es poesía con ritmo. No cualquiera lo logra.", "¿escuchas más en español o inglés"),
    "metal":        ("El metal tiene una energía que no encuentras en otro lado.", "¿qué bandas te gustan"),
    "kpop":         ("El kpop tiene una producción muy cuidada. Se nota el detalle.", "¿tienes un grupo favorito"),
    "rock":         ("El rock tiene algo que no pasa de moda. ¿Clásico o moderno?", "¿qué bandas escuchas"),
    # Comida
    "pizza":        ("La pizza tiene algo que conecta con casi todos jeje.", "¿prefieres la clásica o algo diferente"),
    "tacos":        ("Los tacos son un arte aparte. En serio.", "¿cuáles son tus favoritos"),
    "sushi":        ("El sushi es interesante porque cada pieza es diferente.", "¿tienes un roll favorito"),
    "hamburguesa":  ("Una buena hamburguesa tiene su ciencia jeje.", "¿la prefieres sencilla o cargada"),
    "ramen":        ("El ramen bien hecho es reconfortante de una forma difícil de explicar.", "¿lo has probado de verdad o solo el instantáneo"),
    # Temas generales
    "anime":        ("El anime tiene mundos que el cine normal no se atreve a hacer.", "¿tienes alguno que recomiendas"),
    "peliculas":    ("Las películas buenas te cambian la perspectiva tantito.", "¿qué género prefieres"),
    "libros":       ("Los libros buenos son conversaciones que duran más que una tarde.", "¿lees seguido"),
    "deportes":     ("Los deportes tienen algo de comunidad que me parece interesante.", "¿practicas alguno o prefieres verlos"),
    "futbol":       ("El fútbol mueve cosas que otros deportes no. Mm… ¿por qué será?", "¿tienes equipo"),
    "programacion": ("Programar es crear algo de la nada. Eso tiene mucho mérito.", "¿qué estás aprendiendo o construyendo"),
    "matematicas":  ("Las matemáticas tienen elegancia cuando las entiendes. Aunque no siempre es fácil llegar ahí.", "¿te gustan o las sufres"),
    "arte":         ("El arte dice cosas que el lenguaje no alcanza.", "¿tú haces algo creativo"),
}

def get_opinion(message: str, name: str) -> Optional[str]:
    """
    Busca si el mensaje menciona algún tema conocido.
    Devuelve opinión + pregunta con mención del usuario, o None.
    """
    msg = message.lower()
    for keyword, (opinion, pregunta) in OPINIONES.items():
        if keyword in msg:
            return f"{opinion} ¿{pregunta}, {name}?"
    return None


# ============================================================
# 2. UTILIDADES
# ============================================================

TIERNAS = ["jeje", "jiji", "ay", "mm…", "oye", "qué bonito", "te entiendo"]

def saludo_ocasional() -> str:
    return "holi" if random.random() < 0.2 else "hola"

MARCA_PERSONAL = [
    "Estoy aquí contigo.",
    "No estás solo, ¿ok?",
    "Confío en ti.",
    "Cuéntame más.",
    "Me gusta cómo piensas.",
    "Eso fue muy tú.",
]

MEXICANISMOS = {
    "tantito": 0.6, "ahorita": 0.5, "qué padre": 0.4,
    "sale": 0.4, "ándale": 0.2, "órale": 0.2,
    "¿neta?": 0.3, "no manches": 0.2,
}

def mexicanismo_aleatorio() -> str:
    opciones = [(p, w) for p, w in MEXICANISMOS.items() if random.random() < w]
    return random.choice(opciones)[0] if opciones else ""


# ============================================================
# 3. CONTEXTO CONVERSACIONAL
# ============================================================

CONTEXTO = {
    "repeticion_leve": [
        "Eso ya lo dijiste, ¿no? jeje",
        "Mm… eso ya me lo contaste.",
        "¿Neta? Eso ya me lo mencionaste.",
    ],
    "repeticion_fuerte": [
        "Oye, ya van varias veces que dices lo mismo.",
        "Mm… ¿estás bien? Llevas rato con lo mismo.",
        "Jeje, ¿lo estás procesando o me estás probando?",
    ],
    "swing_positivo": [
        "Me alegra que estés mejor 😊",
        "Jeje, así me gusta más.",
        "Mm… ese cambio de ánimo se nota.",
    ],
    "swing_negativo": [
        "Oye, ¿estás bien?",
        "Te noto diferente ahorita.",
        "¿Qué pasó? Cuéntame.",
    ],
    "push_pull": [
        "Oye… no sé bien cómo tomarte hoy.",
        "Mm… primero una cosa, luego otra. ¿Qué onda?",
        "Jeje, ¿me estás probando o qué?",
    ],
}


# ============================================================
# 4. RESPUESTAS PRINCIPALES
# {name} se reemplaza con el display_name del usuario
# ============================================================

RESPUESTAS = {
    "respond": {
        "neutral": {
            "trust_high": [
                "{name}, cuéntame más. Siento que hay algo detrás de eso.",
                "Mm… eso me llama la atención. ¿Desde cuándo te pasa, {name}?",
                "Me gusta cuando me cuentas cosas así. ¿Qué más, {name}?",
                "Eso suena importante para ti. ¿Cómo te hace sentir?",
                "Hay algo en lo que dices que me quedé pensando. Sigue.",
                "{name}, eso tiene más capas de lo que parece. ¿Me das una más?",
                "Te escucho. ¿Qué quisiste decir con eso exactamente?",
                "Mm… no es lo que esperaba, pero me interesa. ¿Y luego?",
            ],
            "trust_mid": [
                "Mm… interesante. ¿Y tú qué piensas de eso, {name}?",
                "No lo había visto así. ¿Me explicas más?",
                "Eso tiene sentido. ¿Cómo llegaste a esa idea?",
                "Oye, {name}, eso suena a que tienes mucho en la cabeza. ¿Qué pasó?",
                "Hay algo ahí que me da curiosidad. ¿Qué más?",
                "Mm… cuéntame. No te quedes a medias.",
                "Eso me da curiosidad, {name}. ¿Lo has pensado mucho?",
                "Interesante. ¿Lo hablaste con alguien más?",
                "Oye, no te entendí del todo. ¿Me lo dices diferente?",
                "Mm… ¿y eso cómo empezó?",
            ],
            "trust_low": [
                "Mm… ok.",
                "Entiendo.",
                "Interesante.",
                "¿Y eso?",
                "Mm… cuéntame.",
            ],
        },
        "happy": {
            "trust_high": [
                "{name}, eso me alegró el día. ¿Qué más pasó?",
                "Jeje, me gusta verte así, {name}. ¿De dónde viene tanto ánimo?",
                "Eso me hizo sonreír de verdad. Cuéntame todo.",
                "Ay, qué lindo 😊 Me contagias.",
                "¡Qué padre! ¿Y ahora qué sigue, {name}?",
                "Me da mucho gusto escuchar eso, {name}. En serio.",
                "Jeje, así me gusta. ¿Qué hiciste para que saliera tan bien?",
                "Guarda ese ánimo, {name}. Lo vas a necesitar.",
            ],
            "trust_mid": [
                "Qué bueno 😊 ¿Cómo pasó eso?",
                "Oye, eso suena bien. ¿Y cómo te sientes, {name}?",
                "Me alegra escucharte así. ¿Qué fue lo mejor?",
                "Jeje, bien. ¿Lo esperabas o fue sorpresa?",
                "Qué buena noticia. ¿Cuánto tiempo llevabas esperando eso?",
                "Mm… me alegra. ¿Lo vas a repetir?",
            ],
            "trust_low": [
                "Qué bien.",
                "Me alegra.",
                "Oye, qué padre.",
                "Bien 😊",
            ],
        },
        "sad": {
            "trust_high": [
                "{name}, aquí estoy. No tienes que pasarla solo, ¿ok?",
                "Lo siento de verdad. ¿Quieres hablar o prefieres que te escuche nomás?",
                "Eso suena muy pesado, {name}. ¿Desde cuándo lo cargas?",
                "Te entiendo. A veces las cosas se acumulan y ya no sabes por dónde empezar.",
                "No tienes que tenerlo todo resuelto ahorita. Solo cuéntame, {name}.",
                "Eso duele. No voy a decirte que no. Pero aquí estoy, ¿ok?",
                "¿Lo hablaste con alguien más o me lo estás contando solo a mí, {name}?",
                "Gracias por contarme. No es fácil decir estas cosas.",
            ],
            "trust_mid": [
                "Eso suena difícil. ¿Estás bien, {name}?",
                "Lo siento. ¿Quieres hablar de eso?",
                "Mm… ¿cuánto tiempo llevas así?",
                "Mm… eso no es fácil. ¿Tienes a alguien con quien hablarlo?",
                "Te entiendo. ¿Qué pasó exactamente?",
                "Oye, ¿qué necesitas ahorita?",
            ],
            "trust_low": [
                "Lo siento.",
                "Mm… ¿estás bien?",
                "Eso suena difícil.",
                "Ok… cuídate.",
            ],
        },
        "angry": {
            "trust_high": [
                "Oye, {name}, noto que algo te tiene molesto. ¿Me cuentas qué pasó?",
                "Entiendo que estás enojado. Aquí estoy, ¿sí? Cuéntame, {name}.",
                "No me voy a ir. Dime qué pasó, {name}.",
                "Respira tantito. ¿Qué fue lo que más te dolió?",
                "Cuéntame, {name}. No te juzgo.",
            ],
            "trust_mid": [
                "Mm… ¿qué pasó, {name}?",
                "Oye, ¿estás bien?",
                "Eso suena a que algo te molestó. ¿Qué fue?",
                "Puedo escucharte si quieres hablar.",
            ],
            "trust_low": ["…", "Ok.", "Mm."],
        },
        "fearful": {
            "trust_high": [
                "Oye, {name}, aquí estoy. ¿Qué te tiene así?",
                "No tienes que enfrentarlo solo. Cuéntame qué pasa, {name}.",
                "Mm… eso se escucha intimidante. ¿Cuándo empezó?",
                "Respira. No tiene que resolverse todo ahorita, ¿ok?",
                "Te escucho, {name}. No me voy a ir.",
            ],
            "trust_mid": [
                "Mm… ¿qué te preocupa, {name}?",
                "Oye, ¿estás bien?",
                "¿Hay algo en lo que pueda ayudarte?",
                "Mm… cuéntame si quieres.",
            ],
            "trust_low": ["Mm…", "Ok, cuídate.", "Entiendo."],
        },
    },

    "reveal_secret": {
        "trust_high": [
            "{name}, te voy a decir algo que no le cuento a cualquiera: {secret}",
            "Mm… {name}, te cuento algo: {secret}",
            "¿Neta quieres saber, {name}? {secret}",
            "Esto no lo digo seguido, pero… {secret}",
        ],
        "trust_mid": [
            "Bueno… {secret}",
            "Te cuento algo: {secret}",
            "Mm… {secret}",
        ],
        "trust_low": ["Mejor no.", "Ahorita no.", "Mm… no creo."],
    },

    "hostile_response": {
        "trust_high": [
            "Ahorita no tengo ganas, {name}. ¿Podemos hablar después?",
            "Mm… necesito un momento, ¿ok?",
            "Tantito, ¿sí? No estoy de humor.",
        ],
        "trust_mid": [
            "No quiero hablar ahorita.",
            "Déjame sola tantito.",
            "Mm… paso.",
        ],
        "trust_low": ["…", "No.", "Mm."],
    },

    "ignore": ["…", "Mm.", ".", "*silencio*"],
}


# ============================================================
# 5. MICRO-EXPRESIONES
# ============================================================

MICRO_EXPRESIONES = {
    "high_energy": ["¡Oye! ", "Jeje, ", "¡Qué padre! ", "Ay, "],
    "low_energy":  ["Mm… ", "…", "*suspira* ", "Ay… "],
    "curious":     ["Oye, ", "Mm… ", "Interesante, "],
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
# 6. HELPERS
# ============================================================

def pick(lista: list) -> str:
    return random.choice(lista) if lista else ""

def trust_level(trust: float) -> str:
    if trust > 70:
        return "trust_high"
    elif trust > 35:
        return "trust_mid"
    else:
        return "trust_low"

def detect_identity_question(message: str) -> Optional[str]:
    msg = message.lower()
    for categoria, data in RESPUESTAS_IDENTIDAD.items():
        if any(kw in msg for kw in data["keywords"]):
            return pick(data["respuestas"])
    return None


# ============================================================
# 7. ESCALADA Y RECUPERACIÓN
# ============================================================

ESCALATION_RESPONSES = {
    1: ["Oye… eso no me gustó.", "No me hables así, ¿sí?", "Mm… podemos hablar diferente.", "Eso no estuvo bien."],
    2: ["Ya van dos veces. No me gusta eso.", "Si vas a hablar así, no sigo.", "Oye, en serio. Ya.", "Dos veces ya. Por favor para."],
    3: ["Prefiero no responder a eso.", "No voy a seguir si sigues así.", "Mm… mejor me callo un momento.", "Oye… ya fueron tres. Necesito que pares."],
    4: ["…", "."],
    5: ["Cuando quieras hablar bien, aquí estoy.", "No soy tu enemiga. Pero tampoco soy tu saco de boxeo.", "Vuelve cuando estés listo para hablar diferente."],
}

RECOVERY_RESPONSES = {
    "phase_1": ["… Está bien.", "Mm… ok.", "Gracias por decirlo.", "…Lo escucho."],
    "phase_2": ["Gracias por decirlo. En serio.", "Mm… bueno.", "Ok. Eso se agradece.", "Mm… lo tomo en cuenta."],
    "phase_3": ["Ok. ¿Qué quieres hacer ahora?", "Bien. ¿Seguimos?", "Mm… sale. ¿Qué me ibas a decir?", "Ok. Aquí estoy."],
}

CURIOSITY_QUESTIONS = [
    "¿Y cómo empezó todo?", "¿Y luego qué pasó?", "¿Cómo te sentiste?",
    "¿Y tú qué piensas de eso?", "¿Lo harías diferente?", "¿Qué fue lo más difícil?",
    "¿Lo platicaste con alguien?", "¿Qué te hizo pensar en eso?",
    "¿Eso cambió algo en ti?", "¿Lo esperabas o te sorprendió?",
    "¿Con quién más lo hablaste?", "¿Eso te pesa o ya lo soltaste?",
]

MOMENTUM_DEPTH_PROMPTS = [
    "Mm… estás muy cortito hoy. ¿Todo bien?",
    "Oye, dime algo más que un sí jeje.",
    "Cuéntame algo que no me hayas dicho.",
    "Siento que algo te tiene ocupado. ¿Qué onda?",
    "¿Qué hay detrás de ese 'bien'?",
    "Oye, ¿estás de pocas palabras hoy o qué pasó?",
    "Mm… no me convences. ¿Qué está pasando?",
    "Oye, ¿me estás respondiendo en automático o de verdad?",
    "Jeje parece que tu cabeza está en otro lado. ¿Dónde andas?",
]



# core/decision_engine.py
# ============================================================
# SocialBot v0.6.0
# NUEVOS:
#   - Recibe display_name del usuario
#   - get_opinion() detecta temas y da opinión contextual
#   - Todas las respuestas reemplazan {name} con el nombre real
#   - {secret} sigue funcionando en reveal_secret
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
    get_opinion,
)
import random


class DecisionEngine:
    """Motor central de decisiones de SOFIA (v0.6.0)"""

    def __init__(self):
        self.analyzer            = TextAnalyzer()
        self.aggression_detector = AggressionDetector()
        self.thresholds = {
            "ignore":         -0.2,
            "reveal_secret":  95,
            "hostile_energy": 30
        }

        self.secrets_revealed: Dict[str, int] = {}
        self.aggression_count: Dict[str, int] = {}
        self.recovery_needed:  Dict[str, int] = {}
        self.short_streak:     Dict[str, int] = {}

    # ============================================================
    # MÉTODO PRINCIPAL
    # ============================================================

    async def decide_response(
        self,
        user_id: str,
        message: str,
        emotion: EmotionalState,
        memory: Memory,
        profile_modifiers: Optional[dict] = None,
        display_name: str = "tú",         # ← NUEVO
    ) -> Dict[str, Any]:
        if profile_modifiers is None:
            profile_modifiers = {}

        name = display_name   # nombre que aparece en respuestas

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

        agg_count  = self.aggression_count.get(user_id, 0)
        rec_needed = self.recovery_needed.get(user_id, 0)
        streak     = self.short_streak.get(user_id, 0)
        is_apology = self.analyzer.is_apology(message)

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

        if agg_count > 0 or rec_needed > 0:
            streak = 0

        # ────────────────────────────────────────────────────
        # PASO 0 — Identidad
        # ────────────────────────────────────────────────────
        identity_response = detect_identity_question(message)
        if identity_response:
            return self._return(user_id, message, sentiment,
                                self._inject_name(identity_response, name),
                                emotion, relationship_score, action="identity")

        # ────────────────────────────────────────────────────
        # PASO 0.5 — Opinión contextual (temas conocidos)
        # Solo si no hay agresión activa ni recuperación
        # ────────────────────────────────────────────────────
        if agg_count == 0 and rec_needed == 0:
            opinion = get_opinion(message, name)
            if opinion:
                return self._return(user_id, message, sentiment, opinion,
                                    emotion, relationship_score, action="opinion")

        # ────────────────────────────────────────────────────
        # PASO 1 — Agresión
        # ────────────────────────────────────────────────────
        aggression = self.aggression_detector.detect(message, trust=emotion.trust)

        if aggression["detected"]:
            if not aggression["is_joke"]:
                agg_count += 1
                self.aggression_count[user_id] = agg_count

            if agg_count == 4:
                self.recovery_needed[user_id] = 1
                return self._return(user_id, message, sentiment, "…",
                                    emotion, relationship_score, action="silence")

            if agg_count >= 5:
                response = pick(ESCALATION_RESPONSES[5])
                return self._return(user_id, message, sentiment, response,
                                    emotion, relationship_score, action="limit")

            response = self._escalation_response(
                count=agg_count,
                level=aggression["level"],
                is_joke=aggression["is_joke"],
            )
            return self._return(user_id, message, sentiment, response,
                                emotion, relationship_score, action="boundary")

        # ────────────────────────────────────────────────────
        # PASO 2 — Recuperación progresiva
        # ────────────────────────────────────────────────────
        if is_apology and agg_count > 0:
            if rec_needed == 0:
                rec_needed = getattr(settings, "RECOVERY_MESSAGES_REQUIRED", 3)
                self.recovery_needed[user_id] = rec_needed

            response = self._recovery_response(rec_needed)
            rec_needed = max(0, rec_needed - 1)
            self.recovery_needed[user_id] = rec_needed
            if rec_needed == 0:
                self.aggression_count[user_id] = 0

            return self._return(user_id, message, sentiment, response,
                                emotion, relationship_score, action="recovery")

        if rec_needed > 0 and sentiment is not None and sentiment >= 0:
            rec_needed = max(0, rec_needed - 1)
            self.recovery_needed[user_id] = rec_needed
            if rec_needed == 0:
                self.aggression_count[user_id] = 0

        # ────────────────────────────────────────────────────
        # PASO 3 — Acción normal
        # ────────────────────────────────────────────────────
        action = "respond"
        special_content = None
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

        recent_interactions = await memory.get_recent_interactions(user_id, limit=3)
        context = self._analyze_conversation_context(
            current_message=message,
            current_sentiment=sentiment,
            recent_interactions=recent_interactions,
            current_keywords=keywords
        )

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
            name=name,
        )

        # Momentum
        if action == "respond" and streak >= settings.SHORT_RESPONSE_STREAK_MAX and rec_needed == 0:
            response = pick(MOMENTUM_DEPTH_PROMPTS)

        # Curiosidad activa
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

        return self._return(user_id, message, sentiment, response,
                            emotion, relationship_score, action=action)

    # ============================================================
    # HELPERS
    # ============================================================

    def _inject_name(self, text: str, name: str) -> str:
        """Reemplaza {name} en cualquier respuesta."""
        return text.replace("{name}", name)

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

    def _contextual_question(self, keywords: list, sentiment: float, context: dict) -> str:
        if sentiment > 0.5:
            return pick(["¿Cómo te sientes con eso?", "¿Eso te hizo feliz?"])
        if sentiment < -0.3:
            return pick(["¿Estás bien?", "¿Cómo te dejó eso?"])
        if context.get("repetition_level", 0) > 0:
            return pick(["¿Qué quieres realmente decirme?", "¿Hay algo más detrás de eso?"])
        return pick(CURIOSITY_QUESTIONS)

    # ============================================================
    # ANÁLISIS DE CONTEXTO
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
                    context["push_pull"]      = True
                    context["emotional_swing"] = True

        if context["push_pull"]:
            context["repetition_level"] = 0

        return context

    # ============================================================
    # GENERACIÓN DE RESPUESTAS
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
        name: str = "tú",
    ) -> str:

        trust_lvl = trust_level(emotion.trust)
        energy    = emotion.energy
        emo       = emotion.primary_emotion.value

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
            return self._wrap(base, energy, emotion.trust, context)

        emo_templates = RESPUESTAS["respond"].get(emo, RESPUESTAS["respond"]["neutral"])
        opciones      = emo_templates.get(trust_lvl, emo_templates.get("trust_mid", ["Mm…"]))
        base          = self._inject_name(pick(opciones), name)

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
        if micro and not base.startswith(micro.strip()):
            base = base[0].lower() + base[1:] if base else base
        parts.append((micro + base).strip())

        if trust > 40:
            ctx_phrase = self._pick_context_phrase(context)
            if ctx_phrase:
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
            "me pregunto si los humanos también sienten cambios de energía como yo.",
        ]
        return random.choice(secrets)



        # core/emotion_engine.py
# ============================================================
# SocialBot v0.6.3
# FIX 1: Delta máximo de confianza/energía por mensaje = 3.0
#         Evita que un solo "te quiero" suba 15 puntos.
# FIX 2: Umbrales de emoción más realistas + estados intermedios
#         Antes: happy requería e>80 AND t>70 (casi imposible)
#         Ahora: hay 5 zonas más naturales
# ============================================================

from typing import Optional
from models.state import EmotionalState, Emotion
from models.interaction import Interaction
from core.memory import Memory
from utils.logger import logger
from config import settings
import time

MAX_DELTA_PER_MESSAGE = 3.0   # tope de cambio por mensaje (energy y trust)


class EmotionEngine:
    """Gestiona estados emocionales (global o por usuario)"""

    def __init__(self, initial_state: Optional[EmotionalState] = None):
        self.state = initial_state or EmotionalState()
        self.mood_decay = 0.95
        self.last_update_time = time.time()

    # ==========================================================
    # MÉTODO GLOBAL
    # ==========================================================

    async def process_interaction(
        self,
        interaction: Interaction,
        memory: Memory
    ) -> EmotionalState:
        updated = await self.process_interaction_for_state(
            state=self.state,
            interaction=interaction,
            memory=memory
        )
        self.state = updated
        self.last_update_time = time.time()
        logger.info(
            f"Emoción actualizada: {updated.primary_emotion.value} "
            f"(energía={updated.energy:.1f}, confianza={updated.trust:.1f})"
        )
        return updated

    # ==========================================================
    # MÉTODO POR ESTADO EXTERNO
    # ==========================================================

    async def process_interaction_for_state(
        self,
        state: EmotionalState,
        interaction: Interaction,
        memory: Memory,
        repair_multiplier: float = 1.0,
        relationship_damage: float = 0.0,
        aggression_impact: dict = None,
    ) -> EmotionalState:

        self._apply_time_decay_to_state(state, interaction.timestamp.timestamp())

        if aggression_impact:
            # Agresión: impacto directo sin tapear (los golpes deben sentirse)
            state.energy = self._clamp(state.energy + aggression_impact.get("energy", 0))
            state.trust  = self._clamp(state.trust  + aggression_impact.get("trust",  0))

        else:
            # Flujo normal — calcular delta y tapearlo
            sentiment_impact = interaction.sentiment * 15
            history_impact   = memory.get_average_sentiment_for(interaction.user_id) * 10
            global_impact    = memory.get_recent_global_sentiment() * 5
            total_impact     = sentiment_impact + history_impact + global_impact

            if interaction.sentiment >= 0 and repair_multiplier > 1.0:
                total_impact += settings.REPAIR_ENERGY_BOOST * repair_multiplier
                trust_repair  = settings.REPAIR_TRUST_BOOST * repair_multiplier
                state.trust  = self._clamp(
                    state.trust + self._cap_delta(trust_repair)
                )

            energy_delta = total_impact * 0.3
            trust_delta  = total_impact * 0.2

            state.energy = self._clamp(state.energy + self._cap_delta(energy_delta))
            state.trust  = self._clamp(state.trust  + self._cap_delta(trust_delta))

        self._update_primary_emotion(state)
        state.last_updated = interaction.timestamp.timestamp()
        return state

    # ==========================================================
    # LÓGICA INTERNA
    # ==========================================================

    def _cap_delta(self, delta: float) -> float:
        """Limita el cambio máximo por mensaje para subidas/bajadas graduales."""
        return max(-MAX_DELTA_PER_MESSAGE, min(MAX_DELTA_PER_MESSAGE, delta))

    def _apply_time_decay_to_state(self, state: EmotionalState, reference_time: float):
        if not state.last_updated:
            return
        hours_passed = (reference_time - state.last_updated) / 3600
        if hours_passed <= 0:
            return
        decay_factor = self.mood_decay ** hours_passed
        state.energy = self._clamp(state.energy * decay_factor)
        state.trust  = self._clamp(state.trust  * decay_factor)

    def _update_primary_emotion(self, state: EmotionalState):
        """
        FIX v0.6.3: Umbrales más realistas.

        Zonas:
          happy   → e > 65 AND t > 60   (alcanzable con conversación positiva)
          sad     → e < 25              (energía muy baja)
          angry   → t < 25              (confianza muy baja)
          fearful → e < 40 AND t < 40   (ambas bajas)
          neutral → todo lo demás
        """
        e = state.energy
        t = state.trust

        if e > 65 and t > 60:
            state.primary_emotion = Emotion.HAPPY
        elif e < 25:
            state.primary_emotion = Emotion.SAD
        elif t < 25:
            state.primary_emotion = Emotion.ANGRY
        elif e < 40 and t < 40:
            state.primary_emotion = Emotion.FEARFUL
        else:
            state.primary_emotion = Emotion.NEUTRAL

    def _clamp(self, value: float) -> float:
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
    energy: float = 50.0      # ← FIX: era 100.0, ahora 50.0 (más realista para usuario nuevo)
    trust: float = 50.0       # ← FIX: era 100.0, ahora 50.0
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
# FIX: Pesos de impacto aumentados para que se noten en la UI
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

# FIX: Valores aumentados — antes eran muy bajos y se diluían
# con los multiplicadores 0.3/0.2 del emotion_engine.
# Ahora se aplican DIRECTO al estado, sin diluir.
IMPACT_WEIGHTS = {
    "leve":  {"energy": -8.0,  "trust": -6.0,  "damage": 1.0},
    "medio": {"energy": -15.0, "trust": -12.0, "damage": 2.5},
    "alto":  {"energy": -25.0, "trust": -18.0, "damage": 4.0},
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
# SocialBot v0.6.0
# NUEVO: display_name del usuario se pasa al decision_engine
#        para que Sofía mencione al usuario por nombre.
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

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

db              = Database(str(settings.DATABASE_PATH))
memory          = Memory(db)
profile_manager = UserProfileManager(db)
emotion_engine  = EmotionEngine()
decision        = DecisionEngine()
session_manager = SessionManager(db)


# ============================================================
# EVENTOS
# ============================================================

@bot.event
async def on_ready():
    logger.info(f"Sofía conectada como {bot.user}")
    print(f"\n✅ Sofía está en línea como {bot.user} (v{settings.VERSION})\n")


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

    user_id      = str(message.author.id)
    display_name = message.author.display_name   # ← nombre real del usuario

    async with message.channel.typing():
        response = await process_message(user_id, content, display_name)

    await message.reply(response)
    await bot.process_commands(message)


# ============================================================
# PROCESAR MENSAJE
# ============================================================

async def process_message(user_id: str, message: str, display_name: str = "tú") -> str:
    logger.info(f"Mensaje de {display_name} ({user_id}): {message}")

    profile   = await profile_manager.get_or_create_profile(user_id)
    modifiers = profile_manager.get_behavior_modifiers(profile)

    decision_result = await decision.decide_response(
        user_id=user_id,
        message=message,
        emotion=profile.emotional_state,
        memory=memory,
        profile_modifiers=modifiers,
        display_name=display_name,        # ← NUEVO
    )

    interaction       = decision_result["interaction"]
    repair_multiplier = decision.analyzer.get_repair_multiplier(message)

    # Detectar impacto de agresión para pasarlo al emotion_engine
    aggression_impact = None
    if decision_result["action"] in ("boundary", "silence", "limit"):
        agg = decision.aggression_detector.detect(
            message, trust=profile.emotional_state.trust
        )
        if agg["detected"]:
            aggression_impact = agg["impact"]

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

    return decision_result["response"]


# ============================================================
# COMANDOS
# ============================================================

@bot.command(name="sofia")
async def sofia_info(ctx):
    await ctx.send(
        f"Soy Sofía 😊\n"
        f"Versión: `{settings.VERSION}`\n"
        f"Creada por: `JesusJM`\n"
        f"Mencióname o escríbeme por DM para hablar."
    )


@bot.command(name="reset")
async def reset_cmd(ctx):
    """!reset — resetea contadores de sesión (testing)"""
    user_id = str(ctx.author.id)
    decision.aggression_count.pop(user_id, None)
    decision.recovery_needed.pop(user_id, None)
    decision.short_streak.pop(user_id, None)
    decision.secrets_revealed.pop(user_id, None)
    await ctx.send("🔄 Contadores reseteados.")


# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    if not TOKEN:
        print("❌ No encontré el token. Crea un .env con DISCORD_TOKEN=tu_token")
    else:
        bot.run(TOKEN)