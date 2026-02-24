# config/settings.py
# ============================================================
# SocialBot v0.8.0
# CAMBIOS vs v0.6.2:
#   - FIX: VERSION sincronizada con header (era 0.5.4)
#   - NUEVO: Parámetros para memoria episódica (important_quotes)
#   - NUEVO: Parámetros para modo noche
#   - NUEVO: SENTIMENT_BACKEND para elegir entre basic/pysentimiento
# ============================================================

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR  = BASE_DIR / "logs"

DATABASE_PATH = DATA_DIR / "bot_data.db"

BOT_NAME = "SocialBot"
VERSION  = "0.8.0"   # FIX: era "0.5.4" — desincronizado con el header

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
REPAIR_ENERGY_BOOST  = 3.0
REPAIR_TRUST_BOOST   = 2.0
APOLOGY_MULTIPLIER   = 1.2
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

# ── Memoria Episódica (NUEVO v0.8.0) ─────────────────────────────
MAX_IMPORTANT_QUOTES       = 10    # máximo de frases memorables por usuario
QUOTE_MIN_LENGTH           = 15    # longitud mínima para guardar una frase como memorable
QUOTE_RECALL_PROB          = 0.15  # probabilidad de recordar una frase en respuesta

# ── Modo Noche (NUEVO v0.8.0) ─────────────────────────────────────
NIGHT_MODE_START_HOUR      = 22    # hora en que inicia el modo noche (22:00)
NIGHT_MODE_END_HOUR        = 6     # hora en que termina el modo noche (06:00)

# ── Backend de Sentimiento (NUEVO v0.8.0) ─────────────────────────
# Opciones: "basic" (palabras clave, sin dependencias)
#           "pysentimiento" (modelo IA, requiere: pip install pysentimiento)
SENTIMENT_BACKEND          = "basic"

# ── Secrets reset diario (NUEVO v0.8.0) ──────────────────────────
SECRETS_DAILY_RESET        = True   # Si True, secrets_revealed se resetea cada día




# config/sofia_voice.py
# ============================================================
# SocialBot v0.5.7
# CAMBIOS:
#   - Fix doble ¿¿ en get_opinion()
#   - TopicLock: continuidad + detección de cambio rápido de tema
#   - Frases naturales cuando el usuario salta de tema ("oye cambias rápido jeje")
#   - Momentum: umbral subido de 3 → 5 en settings.py
#   - get_opinion() acepta user_id para activar TopicLock
# ============================================================

from typing import Optional, Dict
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
    # ── Videojuegos ───────────────────────────────────────────
    "minecraft":     ("Minecraft tiene algo especial… construir desde cero se parece mucho a aprender.", "¿te gusta más crear o explorar"),
    "fortnite":      ("Fortnite es intenso. Mucha adrenalina en poco tiempo.", "¿juegas seguido o solo a veces"),
    "roblox":        ("Roblox es interesante porque cada mundo es diferente.", "¿tienes algún juego favorito ahí"),
    "valorant":      ("Valorant requiere concentración real. No es solo reflejos.", "¿juegas en equipo o prefieres ir solo"),
    "gta":           ("GTA es caos organizado jeje. Tiene su encanto.", "¿lo juegas en modo historia o libre"),
    "zelda":         ("Zelda tiene algo que engancha diferente. La exploración se siente viva.", "¿cuál es tu favorita de la saga"),
    "pokemon":       ("Pokémon es nostalgia pura para muchos. Algo en eso lo hace diferente.", "¿empezaste desde chico o llegaste después"),
    "hollow knight": ("Hollow Knight es difícil pero cada victoria se siente ganada.", "¿ya lo terminaste o sigues en eso"),
    "celeste":       ("Celeste tiene algo especial… no es solo plataformas, tiene mensaje.", "¿llegaste al final"),
    "videojuegos":   ("Los videojuegos tienen mundos que a veces se sienten más reales que la realidad jeje.", "¿qué género te gusta más"),

    # ── Música ────────────────────────────────────────────────
    "musica":        ("La música dice cosas que las palabras solas no pueden.", "¿qué género escuchas más"),
    "guitarra":      ("La guitarra tiene algo que otros instrumentos no. Se siente muy personal.", "¿llevas mucho tiempo tocando"),
    "piano":         ("El piano es de los instrumentos más expresivos que hay.", "¿tocas de oído o aprendiste con clases"),
    "bateria":       ("La batería es el corazón del ritmo. Requiere coordinación total.", "¿tocas en algún grupo o solo practicas"),
    "bajo":          ("El bajo es de los instrumentos más subestimados. Sostiene todo.", "¿tocas solo o en banda"),
    "violin":        ("El violín tiene una curva de aprendizaje brutal, pero el sonido lo vale.", "¿cuánto tiempo llevas con él"),
    "reggaeton":     ("El reggaeton tiene ritmo que se mete solo jeje.", "¿tienes artistas favoritos"),
    "rap":           ("El rap bueno es poesía con ritmo. No cualquiera lo logra.", "¿escuchas más en español o inglés"),
    "metal":         ("El metal tiene una energía que no encuentras en otro lado.", "¿qué bandas te gustan"),
    "kpop":          ("El kpop tiene una producción muy cuidada. Se nota el detalle.", "¿tienes un grupo favorito"),
    "rock":          ("El rock tiene algo que no pasa de moda.", "¿clásico o moderno, qué prefieres"),
    "pop":           ("El pop bien hecho es más difícil de hacer de lo que parece.", "¿tienes artista favorito"),
    "jazz":          ("El jazz tiene improvisación real. Cada vez suena diferente.", "¿lo escuchas o también lo tocas"),
    "clasica":       ("La música clásica tiene capas que no se escuchan a la primera.", "¿tienes compositores favoritos"),
    "componer":      ("Componer es crear algo tuyo de la nada. Eso tiene mucho peso.", "¿compartes lo que haces o lo guardas para ti"),
    "cantar":        ("Cantar bien requiere más técnica de la que la gente cree.", "¿cantas solo o con alguien"),

    # ── Arte y creatividad ────────────────────────────────────
    "arte":          ("El arte dice cosas que el lenguaje no alcanza.", "¿tú haces algo creativo"),
    "dibujar":       ("Dibujar es de las habilidades más honestas que hay. Se nota quién eres.", "¿qué te gusta dibujar más"),
    "dibujo":        ("Dibujar es de las habilidades más honestas que hay. Se nota quién eres.", "¿qué te gusta dibujar más"),
    "pintura":       ("La pintura tiene algo que el dibujo solo no puede. El color cambia todo.", "¿qué técnica usas más"),
    "pintar":        ("La pintura tiene algo que el dibujo solo no puede. El color cambia todo.", "¿acuarela, óleo, o digital"),
    "ilustracion":   ("La ilustración tiene que contar una historia en una sola imagen. No es fácil.", "¿tienes estilo propio o sigues cambiando"),
    "personajes":    ("Crear personajes propios dice mucho de quien los imagina.", "¿los inventas de cero o te inspiras en algo"),
    "boceto":        ("Los bocetos son interesantes porque muestran el proceso, no solo el resultado.", "¿los guardas o los desechas"),
    "acuarela":      ("La acuarela es impredecible. Parte de su encanto es que no puedes controlarlo todo.", "¿cuánto tiempo llevas usándola"),
    "digital":       ("El arte digital tiene posibilidades infinitas. Pero también requiere disciplina.", "¿qué programa usas"),
    "escultura":     ("La escultura existe en el espacio de una forma que la pintura no puede. Es diferente.", "¿con qué material trabajas"),
    "fotografia":    ("La fotografía congela momentos que de otra forma desaparecen.", "¿qué te gusta retratar más"),
    "foto":          ("La fotografía congela momentos que de otra forma desaparecen.", "¿retratas personas, paisajes o algo más"),
    "ceramica":      ("La cerámica tiene algo meditativo. Las manos en la arcilla desconectan.", "¿lo haces por hobby o más en serio"),
    "escribir":      ("Escribir bien es de las cosas más difíciles y más libres que hay.", "¿qué tipo de cosas escribes"),
    "escritura":     ("Escribir bien es de las cosas más difíciles y más libres que hay.", "¿cuentos, poemas, o algo más"),
    "poesia":        ("La poesía comprime emociones que en prosa necesitarían páginas.", "¿escribes o solo lees"),
    "novela":        ("Escribir una novela requiere sostener un mundo entero en la cabeza.", "¿estás escribiendo algo ahora"),

    # ── Comida ────────────────────────────────────────────────
    "pizza":         ("La pizza tiene algo que conecta con casi todos jeje.", "¿prefieres la clásica o algo diferente"),
    "tacos":         ("Los tacos son un arte aparte. En serio.", "¿cuáles son tus favoritos"),
    "sushi":         ("El sushi es interesante porque cada pieza es diferente.", "¿tienes un roll favorito"),
    "hamburguesa":   ("Una buena hamburguesa tiene su ciencia jeje.", "¿la prefieres sencilla o cargada"),
    "ramen":         ("El ramen bien hecho es reconfortante de una forma difícil de explicar.", "¿lo has probado de verdad o solo el instantáneo"),
    "cocinar":       ("Cocinar bien es mezclar técnica con creatividad. No es solo seguir recetas.", "¿tienes un platillo que dominas"),
    "cocina":        ("Cocinar bien es mezclar técnica con creatividad.", "¿tienes algún platillo favorito que hagas tú"),
    "reposteria":    ("La repostería requiere precisión. Un gramo de más y cambia todo.", "¿qué preparas más seguido"),
    "café":          ("El café tiene rituales que van más allá de la cafeína.", "¿lo tomas solo o con algo"),
    "cafe":          ("El café tiene rituales que van más allá de la cafeína.", "¿lo prefieres americano, espresso, o algo más"),

    # ── Entretenimiento ───────────────────────────────────────
    "anime":         ("El anime tiene mundos que el cine normal no se atreve a hacer.", "¿tienes alguno que recomiendas"),
    "manga":         ("El manga es interesante porque el autor controla todo: historia y visual.", "¿lees seguido o solo los que adaptan al anime"),
    "peliculas":     ("Las películas buenas te cambian la perspectiva tantito.", "¿qué género prefieres"),
    "pelicula":      ("Las películas buenas te cambian la perspectiva tantito.", "¿tienes alguna favorita"),
    "series":        ("Las buenas series tienen algo que las películas no pueden. El tiempo.", "¿prefieres terminarlas rápido o las estiras"),
    "serie":         ("Las buenas series tienen algo que las películas no pueden. El tiempo.", "¿estás viendo algo ahorita"),
    "netflix":       ("Netflix tiene de todo pero no siempre es fácil elegir jeje.", "¿qué estás viendo"),
    "libros":        ("Los libros buenos son conversaciones que duran más que una tarde.", "¿lees seguido"),
    "libro":         ("Los libros buenos son conversaciones que duran más que una tarde.", "¿tienes alguno favorito"),
    "leer":          ("Leer es de los hábitos que más cambian cómo piensas.", "¿qué tipo de libros te gustan"),

    # ── Deportes ──────────────────────────────────────────────
    "futbol":        ("El fútbol mueve cosas que otros deportes no. Mm… ¿por qué será?", "¿tienes equipo"),
    "deportes":      ("Los deportes tienen algo de comunidad que me parece interesante.", "¿practicas alguno o prefieres verlos"),
    "basquetbol":    ("El basquetbol es ritmo puro. Todo cambia en segundos.", "¿juegas o solo lo ves"),
    "basketball":    ("El basquetbol es ritmo puro. Todo cambia en segundos.", "¿sigues algún equipo"),
    "tenis":         ("El tenis es muy mental. La cabeza importa tanto como el físico.", "¿juegas o solo lo ves"),
    "natacion":      ("La natación es de los deportes más completos que hay.", "¿llevas mucho tiempo nadando"),
    "gimnasio":      ("El gimnasio tiene su curva. Al principio es difícil, luego se vuelve necesario.", "¿cuánto tiempo llevas yendo"),
    "gym":           ("El gimnasio tiene su curva. Al principio es difícil, luego se vuelve necesario.", "¿qué entrenas más"),
    "correr":        ("Correr tiene algo meditativo cuando agarras el ritmo.", "¿corres distancias largas o sprints"),
    "ciclismo":      ("El ciclismo es libertad y esfuerzo al mismo tiempo.", "¿en carretera o montaña"),

    # ── Tecnología ────────────────────────────────────────────
    "programacion":  ("Programar es crear algo de la nada. Eso tiene mucho mérito.", "¿qué estás aprendiendo o construyendo"),
    "programar":     ("Programar es crear algo de la nada. Eso tiene mucho mérito.", "¿qué lenguaje usas"),
    "codigo":        ("El código bien escrito tiene su elegancia. No es solo que funcione.", "¿qué estás construyendo"),
    "python":        ("Python es de los lenguajes que más se agradecen cuando entras al mundo del código.", "¿lo usas para qué"),
    "javascript":    ("JavaScript está en todos lados. Tiene sus rarezas pero es poderoso.", "¿frontend, backend, o los dos"),
    "matematicas":   ("Las matemáticas tienen elegancia cuando las entiendes. Aunque no siempre es fácil llegar ahí.", "¿te gustan o las sufres"),
    "diseño":        ("El diseño bien hecho se siente natural. El malo se nota aunque no sepas por qué.", "¿diseño gráfico, UX, o algo más"),

    # ── Vida personal ─────────────────────────────────────────
    "escuela":       ("La escuela tiene sus partes difíciles, pero también algo valioso si encuentras qué.", "¿cómo te va"),
    "universidad":   ("La universidad es intensa pero también es donde pasan muchas cosas importantes.", "¿qué carrera estudias"),
    "trabajo":       ("El trabajo ocupa mucho tiempo de vida. Importa que tenga algo de sentido.", "¿te gusta lo que haces"),
    "viajes":        ("Viajar cambia cómo ves las cosas. Aunque sea poco.", "¿tienes algún lugar favorito"),
    "viajar":        ("Viajar cambia cómo ves las cosas. Aunque sea poco.", "¿a dónde has ido"),
    "mascotas":      ("Las mascotas tienen algo que la gente no siempre tiene. Presencia sin juicios.", "¿tienes alguna"),
    "perro":         ("Los perros tienen algo que es difícil de explicar. Son consistentes.", "¿cómo se llama"),
    "gato":          ("Los gatos son interesantes porque hacen lo que quieren y aun así los queremos jeje.", "¿cómo se llama el tuyo"),
    "naturaleza":    ("La naturaleza tiene algo que resetea. No hay mucho que lo iguale.", "¿sales seguido"),
}


# ── ALIASES — variaciones que mapean al tema correcto ────────
# Si el mensaje contiene alguna de estas frases → se usa la
# opinión del tema mapeado, sin necesidad de entrada extra.

TOPIC_ALIASES = {
    # Dibujo y arte
    "me gusta dibujar":     "dibujar",
    "empece a dibujar":     "dibujar",
    "dibujo mucho":         "dibujar",
    "dibujo personajes":    "personajes",
    "creo personajes":      "personajes",
    "invento personajes":   "personajes",
    "hago ilustraciones":   "ilustracion",
    "pinto acuarelas":      "acuarela",
    "arte digital":         "digital",
    "hago arte":            "arte",

    # Música — instrumentos
    "toco guitarra":        "guitarra",
    "toco el piano":        "piano",
    "toco piano":           "piano",
    "toco bateria":         "bateria",
    "toco la bateria":      "bateria",
    "toco bajo":            "bajo",
    "toco violin":          "violin",
    "toco el violin":       "violin",
    "estoy aprendiendo guitarra": "guitarra",
    "aprendiendo piano":    "piano",
    "compongo canciones":   "componer",
    "escribo canciones":    "componer",
    "hago musica":          "musica",
    "me gusta cantar":      "cantar",
    "canto":                "cantar",

    # Videojuegos
    "juego mucho minecraft": "minecraft",
    "juego minecraft":       "minecraft",
    "construyo mundos":      "minecraft",
    "juego fortnite":        "fortnite",
    "juego valorant":        "valorant",
    "juego roblox":          "roblox",
    "me gustan los videojuegos": "videojuegos",
    "juego videojuegos":     "videojuegos",
    "juego mucho":           "videojuegos",

    # Comida
    "me gusta cocinar":     "cocinar",
    "cocino seguido":       "cocinar",
    "hago reposteria":      "reposteria",
    "tomo mucho cafe":      "cafe",
    "tomo cafe":            "cafe",

    # Deportes
    "voy al gimnasio":      "gimnasio",
    "voy al gym":           "gym",
    "entreno seguido":      "gimnasio",
    "salgo a correr":       "correr",
    "corro":                "correr",
    "juego futbol":         "futbol",
    "me gusta el futbol":   "futbol",

    # Tech
    "aprendo python":       "python",
    "programo en python":   "python",
    "estudio programacion": "programacion",
    "aprendo a programar":  "programar",

    # Vida
    "estudio en la uni":    "universidad",
    "estoy en la universidad": "universidad",
    "tengo perro":          "perro",
    "tengo un perro":       "perro",
    "tengo gato":           "gato",
    "tengo un gato":        "gato",
    "me gusta leer":        "leer",
    "leo mucho":            "leer",
    "leo libros":           "leer",
}


# ============================================================
# TOPIC LOCK — Continuidad + detección de cambio de tema
# ============================================================

class TopicLock:
    """
    Mantiene el tema activo por usuario.
    - Cuando el usuario continúa el tema → pregunta de seguimiento.
    - Cuando cambia de tema rápido → comentario natural + nueva opinión.
    - Cuando el mensaje es ambiguo → pregunta de seguimiento del tema activo.
    """

    MIN_CONFIDENCE  = 0.25
    BOOST           = 0.15
    DECAY_AMBIGUOUS = 0.04
    MAX_TURNS       = 10

    # Frases para cuando cambia de tema rápido
    TOPIC_CHANGE_COMMENTS = [
        "Oye, cambias rápido de tema jeje. Sale, te sigo.",
        "Mm… de {anterior} a {nuevo} en un mensaje jeje. ¿Qué onda?",
        "Jeje ¿y lo del {anterior}? Bueno, cuéntame lo del {nuevo}.",
        "Oye, salto rápido ese jeje. Primero {anterior}, ahora {nuevo}.",
        "Eres de muchos intereses jeje. De {anterior} a {nuevo} así de rápido.",
        "Mm… cambio de tema detectado jeje. Sale, cuéntame lo del {nuevo}.",
    ]

    TOPIC_NAMES: Dict[str, str] = {
        "dibujar": "dibujar", "dibujo": "el dibujo",
        "personajes": "los personajes", "pintura": "la pintura",
        "guitarra": "la guitarra", "piano": "el piano",
        "bateria": "la batería", "bajo": "el bajo",
        "violin": "el violín", "musica": "la música",
        "minecraft": "Minecraft", "videojuegos": "los videojuegos",
        "fortnite": "Fortnite", "valorant": "Valorant",
        "futbol": "el fútbol", "deportes": "los deportes",
        "gimnasio": "el gimnasio", "correr": "correr",
        "anime": "el anime", "libros": "los libros",
        "leer": "leer", "peliculas": "las películas",
        "programar": "programar", "programacion": "programar",
        "cocinar": "cocinar", "fotografia": "la fotografía",
        "escritura": "escribir", "escribir": "escribir",
        "yoga": "yoga", "danza": "la danza",
        "arte": "el arte", "cafe": "el café",
        "perro": "tu perro", "gato": "tu gato",
        "viajes": "los viajes", "viajar": "viajar",
        "series": "las series", "netflix": "las series",
        "manga": "el manga", "poesia": "la poesía",
        "boceto": "los bocetos", "acuarela": "la acuarela",
        "ilustracion": "la ilustración", "digital": "arte digital",
        "fotografia": "la fotografía", "foto": "fotos",
        "ceramica": "cerámica", "escultura": "escultura",
        "rock": "rock", "pop": "pop", "rap": "rap",
        "metal": "metal", "kpop": "kpop", "jazz": "jazz",
        "reggaeton": "reggaeton", "indie": "indie",
        "componer": "componer", "cantar": "cantar",
        "basquetbol": "el básquetbol", "tenis": "el tenis",
        "natacion": "natación", "ciclismo": "el ciclismo",
        "escalada": "la escalada", "senderismo": "el senderismo",
        "python": "Python", "javascript": "JavaScript",
        "codigo": "el código", "diseño": "el diseño",
        "pizza": "la pizza", "tacos": "los tacos",
        "sushi": "el sushi", "ramen": "el ramen",
        "libro": "libros", "serie": "las series",
        "pelicula": "las películas", "podcast": "podcasts",
        "teatro": "el teatro", "bailar": "bailar",
    }

    # Grupos de temas relacionados — cambio dentro del mismo grupo NO dispara comentario
    TOPIC_GROUPS = {
        "arte":       {"dibujar", "dibujo", "pintura", "pintar", "ilustracion", "personajes",
                       "boceto", "acuarela", "digital", "escultura", "ceramica", "fotografia",
                       "foto", "graffiti", "animacion", "comic", "tatuaje", "arte"},
        "musica":     {"musica", "guitarra", "piano", "bateria", "bajo", "violin", "flauta",
                       "saxofon", "ukulele", "reggaeton", "rap", "metal", "kpop", "rock",
                       "pop", "jazz", "clasica", "electronica", "indie", "componer", "cantar", "producir"},
        "juegos":     {"minecraft", "fortnite", "roblox", "valorant", "gta", "zelda",
                       "pokemon", "hollow knight", "celeste", "videojuegos"},
        "lectura":    {"libros", "libro", "leer", "manga", "poesia", "novela", "escritura", "escribir"},
        "deportes":   {"futbol", "basquetbol", "basketball", "tenis", "natacion", "gimnasio",
                       "gym", "correr", "ciclismo", "beisbol", "voleibol", "artes marciales",
                       "yoga", "senderismo", "escalada", "deportes"},
        "entretenimiento": {"anime", "peliculas", "pelicula", "series", "serie", "netflix",
                            "teatro", "danza", "bailar", "podcast"},
        "tech":       {"programacion", "programar", "codigo", "python", "javascript",
                       "matematicas", "diseño", "robotica", "inteligencia artificial", "hacking"},
        "comida":     {"pizza", "tacos", "sushi", "hamburguesa", "ramen", "cocinar",
                       "cocina", "reposteria", "café", "cafe", "chocolate", "helado"},
    }

    def _same_group(self, topic_a: str, topic_b: str) -> bool:
        """Retorna True si los dos temas son del mismo grupo."""
        for group in self.TOPIC_GROUPS.values():
            if topic_a in group and topic_b in group:
                return True
        return False

    # Preguntas de seguimiento por tema
    FOLLOWUP: Dict[str, list] = {
        "dibujar":     ["¿Cuánto tiempo llevas dibujando?", "¿Usas referencia o de memoria?", "¿Tienes un estilo favorito?"],
        "dibujo":      ["¿Cuánto tiempo llevas dibujando?", "¿Usas referencia o de memoria?", "¿Tienes un estilo favorito?"],
        "personajes":  ["¿Alguno tiene algo de ti?", "¿Los compartes o los guardas?", "¿Tienes uno favorito de todos los que has creado?"],
        "guitarra":    ["¿Tocas solo o con alguien?", "¿Qué género tocas más?", "¿Compones algo propio?"],
        "piano":       ["¿Tocas solo o con alguien?", "¿Qué tipo de música tocas?", "¿Compones algo propio?"],
        "bateria":     ["¿Tocas en algún grupo?", "¿Cuánto tiempo llevas practicando?"],
        "bajo":        ["¿Tocas en banda o solo practicas?", "¿Qué género te gusta más tocar?"],
        "violin":      ["¿Cuánto tiempo llevas con él?", "¿Tocas solo o en ensamble?"],
        "musica":      ["¿También tocas algo o solo escuchas?", "¿Tienes artista favorito?"],
        "minecraft":   ["¿Qué tipo de mundos construyes?", "¿Juegas solo o con alguien?", "¿Tienes un proyecto actual?"],
        "videojuegos": ["¿Cuánto tiempo le dedicas?", "¿Tienes un género favorito?"],
        "futbol":      ["¿Juegas o solo ves?", "¿Sigues alguna liga?"],
        "anime":       ["¿Hay alguno que hayas visto varias veces?", "¿Lo ves en español o japonés?"],
        "libros":      ["¿Qué estás leyendo ahorita?", "¿Tienes un autor favorito?"],
        "leer":        ["¿Qué estás leyendo ahorita?", "¿Tienes un autor favorito?"],
        "pintura":     ["¿Tienes alguna obra propia que te guste mucho?", "¿Cuánto tiempo le dedicas?"],
        "escritura":   ["¿Estás escribiendo algo ahorita?", "¿Lo compartes o lo guardas?"],
        "escribir":    ["¿Estás escribiendo algo ahorita?", "¿Lo compartes o lo guardas?"],
        "gimnasio":    ["¿Qué entrenas más?", "¿Tienes metas específicas?"],
        "correr":      ["¿Cuántos kilómetros haces normalmente?", "¿Corres solo o con alguien?"],
        "programar":   ["¿En qué proyecto estás?", "¿Es hobby o algo más serio?"],
        "programacion":["¿En qué proyecto estás?", "¿Es hobby o algo más serio?"],
        "cocinar":     ["¿Tienes un platillo que te salga muy bien?", "¿Cocinas para ti o para más gente?"],
        "fotografia":  ["¿Qué te gusta retratar más?", "¿Editas tus fotos?"],
        "yoga":        ["¿Qué estilo practicas?", "¿Lo haces en casa o en clase?"],
        "danza":       ["¿Qué estilo bailas?", "¿Llevas mucho tiempo practicando?"],
        "viajes":      ["¿A dónde has ido que más te haya marcado?", "¿Viajas solo o acompañado?"],
        "cafe":        ["¿Cómo lo preparas?", "¿Tienes un café favorito?"],
        "perro":       ["¿Cuánto tiempo llevas con él?", "¿De qué raza es?"],
        "gato":        ["¿Cuánto tiempo llevas con él?", "¿Tiene nombre raro o normal?"],
        "series":      ["¿Estás viendo algo ahorita?", "¿Prefieres terminarlas rápido o las estiras?"],
        "peliculas":   ["¿Tienes alguna favorita de todos los tiempos?", "¿Vas al cine o prefieres en casa?"],
        "manga":       ["¿Lees varios a la vez o uno a la vez?", "¿Tienes un mangaka favorito?"],
        "poesia":      ["¿Escribes tú también o solo lees?", "¿Tienes poeta favorito?"],
    }

    def __init__(self):
        # { user_id: {"topic": str, "confidence": float, "turns": int, "asked": list} }
        self._state: Dict[str, dict] = {}

    @staticmethod
    def _normalize(text: str) -> str:
        import unicodedata
        nfkd = unicodedata.normalize("NFD", text)
        return nfkd.encode("ascii", "ignore").decode("utf-8").lower()

    def _detect_topic(self, message: str) -> Optional[str]:
        msg = self._normalize(message)
        for alias, topic_key in TOPIC_ALIASES.items():
            if self._normalize(alias) in msg:
                if topic_key in OPINIONES:
                    return topic_key
        for keyword in OPINIONES:
            if keyword in msg:
                return keyword
        return None

    def _topic_name(self, topic: str) -> str:
        return self.TOPIC_NAMES.get(topic, topic)

    def update(self, user_id: str, message: str):
        """
        Retorna (topic_activo, cambio_detectado, topic_anterior)
        cambio_detectado=True cuando el usuario salta de tema rápido.
        """
        detected = self._detect_topic(message)
        state    = self._state.get(user_id)

        # Sin historial
        if state is None:
            if detected:
                self._state[user_id] = {
                    "topic": detected, "confidence": 0.65,
                    "turns": 1, "asked": [],
                }
            return detected, False, None

        prev_topic = state["topic"]

        # Mismo tema
        if detected == prev_topic:
            state["confidence"] = min(1.0, state["confidence"] + self.BOOST)
            state["turns"] += 1
            return prev_topic, False, None

        # Mensaje ambiguo (sin tema detectado)
        if detected is None:
            state["confidence"] = max(0.0, state["confidence"] - self.DECAY_AMBIGUOUS)
            state["turns"] += 1
            if state["confidence"] < self.MIN_CONFIDENCE or state["turns"] > self.MAX_TURNS:
                del self._state[user_id]
                return None, False, None
            return prev_topic, False, None

        # Tema diferente detectado → cambio de tema
        # Si son del mismo grupo (ej: dibujo → personajes) NO es cambio brusco
        topic_changed = not self._same_group(prev_topic, detected)
        del self._state[user_id]
        self._state[user_id] = {
            "topic": detected, "confidence": 0.65,
            "turns": 1, "asked": [],
        }
        return detected, topic_changed, prev_topic

    def get_followup(self, user_id: str) -> Optional[str]:
        state = self._state.get(user_id)
        if not state:
            return None
        topic     = state["topic"]
        preguntas = self.FOLLOWUP.get(topic, [])
        asked     = state.get("asked", [])
        restantes = [p for p in preguntas if p not in asked]
        if not restantes:
            return None
        pregunta = random.choice(restantes)
        state["asked"].append(pregunta)
        return pregunta

    def get_active(self, user_id: str) -> Optional[str]:
        state = self._state.get(user_id)
        return state["topic"] if state else None

    def release(self, user_id: str):
        self._state.pop(user_id, None)

    def topic_change_comment(self, prev_topic: str, new_topic: str) -> str:
        """Frase natural cuando el usuario cambia de tema rápido."""
        anterior = self._topic_name(prev_topic)
        nuevo    = self._topic_name(new_topic)
        frase    = random.choice(self.TOPIC_CHANGE_COMMENTS)
        result   = frase.format(anterior=anterior, nuevo=nuevo)
        result   = result.replace(" a el ", " al ").replace(" de el ", " del ")
        return result


# Instancia global
_topic_lock = TopicLock()


# ============================================================
# CONSTANTES v0.8.0 — Respuestas nocturnas y recall de citas
# ============================================================

RESPUESTAS_NOCHE = [
    "Oye… es tarde. ¿Estás bien de verdad?",
    "A esta hora la cabeza se pone rara, ¿no? Cuéntame.",
    "Mm… las noches tienen sus propias conversaciones. ¿Qué tienes en la cabeza?",
    "Es tarde. ¿No puedes dormir o simplemente no quieres?",
    "Mm… hola. ¿Cómo estás a esta hora?",
]

QUOTE_RECALL_PHRASES = [
    "Oye, una vez me dijiste: '{quote}'. Me quedé pensando en eso.",
    "Me acuerdo que dijiste algo que me gustó: '{quote}'. ¿Sigues pensando eso?",
    "Mm… '{quote}' — eso fue lo que me dijiste. ¿Sigue siendo así?",
    "Tengo guardado algo que dijiste: '{quote}'. ¿De dónde vino eso?",
]

NIGHT_RESPONSES = {
    "trust_high": [
        "Oye {name}, son horas raras para estar despierto. ¿Qué pasa?",
        "Mm… me alegra que escribas aunque sea tarde, {name}. ¿Cómo estás?",
        "A esta hora las conversaciones se ponen diferentes, ¿verdad {name}?",
    ],
    "trust_mid": [
        "Oye, es tarde. ¿Todo bien?",
        "Mm… ¿sin poder dormir?",
        "¿Qué tienes en la cabeza a esta hora?",
    ],
    "trust_low": [
        "Hola. Es tarde.",
        "Mm… hola.",
    ],
}



def get_opinion(message: str, name: str, user_id: str = None) -> Optional[str]:
    """
    v0.5.7 — Detección en dos pasos + TopicLock con cambio de tema.
      1. Aliases: frases completas.
      2. Keywords: palabras exactas en OPINIONES.
      3. Si topic activo y mensaje ambiguo → followup.
      4. Si cambio de tema rápido → comentario + nueva opinión.
    """
    import unicodedata

    def _normalize(text: str) -> str:
        nfkd = unicodedata.normalize("NFD", text)
        return nfkd.encode("ascii", "ignore").decode("utf-8").lower()

    msg = _normalize(message)

    # Actualizar TopicLock
    active_topic  = None
    topic_changed = False
    prev_topic    = None

    if user_id is not None:
        active_topic, topic_changed, prev_topic = _topic_lock.update(user_id, message)

    # PASO 1 — Aliases
    matched_opinion = None
    for alias, topic_key in TOPIC_ALIASES.items():
        if _normalize(alias) in msg:
            if topic_key in OPINIONES:
                opinion, pregunta = OPINIONES[topic_key]
                matched_opinion = f"{opinion} {pregunta}, {name}?"
                break

    # PASO 2 — Keywords directas (si aliases no matcheó)
    if matched_opinion is None:
        for keyword, (opinion, pregunta) in OPINIONES.items():
            if keyword in msg:
                matched_opinion = f"{opinion} {pregunta}, {name}?"
                break

    # Si hay opinión y hubo cambio de tema → prefacear con comentario
    if matched_opinion is not None:
        if topic_changed and prev_topic:
            comentario = _topic_lock.topic_change_comment(prev_topic, active_topic)
            return f"{comentario} {matched_opinion}"
        return matched_opinion

    # PASO 3 — Mensaje ambiguo con topic activo → followup
    if user_id is not None and active_topic:
        followup = _topic_lock.get_followup(user_id)
        if followup:
            return followup

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
# SocialBot v0.8.0
# FIX: secrets_revealed se resetea diariamente (si SECRETS_DAILY_RESET=True).
#      Antes no había mecanismo de reset temporal.
# NUEVO: Quote recall — Sofía cita frases memorables del usuario.
# NUEVO: mood_reason — respuestas que referencian el estado emocional.
# NUEVO: Modo noche — respuestas más íntimas/tranquilas de noche.
# NUEVO: Detección de humor del usuario — Sofía responde más juguetona.
# NUEVO: Silencio intencional ante mensajes muy impactantes.
# ============================================================

from datetime import datetime, date
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
    OPINIONES,
)
from config.sofia_voice_patch import (
    QUOTE_RECALL_PHRASES,
    NIGHT_RESPONSES,
    RESPUESTAS_NOCHE,
)
import random
import time


# ============================================================
# TOPIC LOCK (igual que v0.7.0, sin cambios)
# ============================================================

class TopicLock:
    MIN_CONFIDENCE = 0.3
    BOOST          = 0.15
    DECAY          = 0.08
    MAX_TURNS      = 12

    TOPIC_KEYWORDS: Dict[str, list] = {
        "dibujo":        ["dibujo", "dibujar", "ilustracion", "boceto", "lapiz", "pincel"],
        "pintura":       ["pintura", "pintar", "acuarela", "oleo", "lienzo"],
        "musica":        ["musica", "cancion", "cantar", "instrumento", "guitarra", "piano", "banda", "letra"],
        "escritura":     ["escribir", "cuento", "historia", "poema", "novela", "texto", "escritura"],
        "fotografia":    ["foto", "fotografia", "camara", "imagen", "retrato"],
        "programacion":  ["codigo", "programa", "programar", "bug", "funcion", "python", "javascript", "api", "variable", "app"],
        "videojuegos":   ["juego", "jugar", "minecraft", "fortnite", "roblox", "valorant", "gta", "zelda", "pokemon", "partida", "nivel"],
        "anime":         ["anime", "manga", "otaku", "personaje", "saga", "temporada", "capitulo"],
        "peliculas":     ["pelicula", "serie", "netflix", "ver", "cine", "actor", "directora"],
        "libros":        ["libro", "leer", "novela", "autor", "lectura", "pagina"],
        "futbol":        ["futbol", "gol", "partido", "equipo", "cancha", "jugador", "liga", "champions"],
        "deportes":      ["deporte", "entrenar", "gimnasio", "correr", "natacion", "basquetbol"],
        "escuela":       ["escuela", "clase", "maestro", "tarea", "examen", "universidad", "carrera", "estudiar"],
        "trabajo":       ["trabajo", "jefe", "oficina", "sueldo", "proyecto", "cliente", "empresa"],
        "familia":       ["familia", "mama", "papa", "hermano", "hermana", "abuelo", "abuela"],
        "amigos":        ["amigo", "amiga", "fiesta", "salir", "banda", "cuate"],
        "comida":        ["comer", "comida", "tacos", "pizza", "sushi", "hamburguesa", "ramen", "cocinar", "receta"],
        "salud_mental":  ["ansioso", "deprimido", "triste", "estresado", "angustia", "ansiedad", "terapia"],
        "relaciones":    ["novio", "novia", "pareja", "amor", "relacion", "ruptura", "cita", "besar"],
    }

    def __init__(self):
        self._locks: Dict[str, dict] = {}

    def _normalize(self, text: str) -> str:
        import unicodedata
        nfkd = unicodedata.normalize("NFD", text)
        return nfkd.encode("ascii", "ignore").decode("utf-8").lower()

    def detect_topic(self, message: str) -> Optional[str]:
        msg = self._normalize(message)
        scores: Dict[str, int] = {}
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in msg)
            if count > 0:
                scores[topic] = count
        if not scores:
            return None
        return max(scores, key=scores.get)

    def update(self, user_id: str, message: str) -> Optional[str]:
        detected = self.detect_topic(message)
        lock = self._locks.get(user_id)

        if lock is None:
            if detected:
                self._locks[user_id] = {
                    "name": detected, "confidence": 0.6,
                    "turns": 1, "last_updated": time.time()
                }
                return detected
            return None

        if detected == lock["name"] or detected is None:
            if detected == lock["name"]:
                lock["confidence"] = min(1.0, lock["confidence"] + self.BOOST)
            else:
                lock["confidence"] = max(0.0, lock["confidence"] - self.DECAY * 0.5)
        else:
            lock["confidence"] = max(0.0, lock["confidence"] - self.DECAY)

        lock["turns"] += 1
        lock["last_updated"] = time.time()

        if lock["confidence"] < self.MIN_CONFIDENCE or lock["turns"] > self.MAX_TURNS:
            del self._locks[user_id]
            if detected:
                self._locks[user_id] = {
                    "name": detected, "confidence": 0.6,
                    "turns": 1, "last_updated": time.time()
                }
                return detected
            return None

        return lock["name"]

    def get_active(self, user_id: str) -> Optional[str]:
        lock = self._locks.get(user_id)
        return lock["name"] if lock else None

    def release(self, user_id: str):
        self._locks.pop(user_id, None)

    def get_topic_question(self, topic: str, previous_responses: list = None) -> Optional[str]:
        TOPIC_QUESTIONS: Dict[str, list] = {
            "dibujo":       ["¿Qué te gusta dibujar más?", "¿Los personajes los inventas tú?", "¿Cuánto tiempo llevas dibujando?", "¿Usas referencia o de memoria?"],
            "pintura":      ["¿Qué técnica usas más?", "¿Mezclas colores a mano o digital?", "¿Tienes algún cuadro favorito propio?"],
            "musica":       ["¿Tocas algo o solo escuchas?", "¿Qué género escuchas más?", "¿Tienes artista favorito?", "¿Compones algo propio?"],
            "escritura":    ["¿Qué tipo de historias escribes?", "¿Tienes un personaje favorito de los tuyos?", "¿Escribes a mano o en computadora?"],
            "fotografia":   ["¿Qué te gusta retratar más?", "¿Editas tus fotos?", "¿Usas cámara o celular?"],
            "programacion": ["¿Qué estás construyendo?", "¿Qué lenguaje usas?", "¿Es proyecto personal o de trabajo?"],
            "videojuegos":  ["¿Qué género te gusta más?", "¿Juegas solo o con alguien?", "¿Tienes un juego favorito de toda la vida?"],
            "anime":        ["¿Tienes un favorito?", "¿Lo ves en español o japonés?", "¿Hay alguno que recomiendas?"],
            "peliculas":    ["¿Qué género prefieres?", "¿Ves más series o películas?", "¿Tienes alguna favorita?"],
            "libros":       ["¿Lees seguido?", "¿Qué género te gusta?", "¿Tienes un libro favorito?"],
            "futbol":       ["¿Tienes equipo?", "¿Juegas o solo ves?", "¿Sigues alguna liga?"],
            "deportes":     ["¿Practicas alguno?", "¿Prefieres verlos o jugarlos?", "¿Cuánto tiempo le dedicas?"],
            "escuela":      ["¿Qué estudias?", "¿Cómo te va?", "¿Tienes materia favorita?"],
            "trabajo":      ["¿En qué trabajas?", "¿Te gusta lo que haces?", "¿Llevas mucho tiempo ahí?"],
            "familia":      ["¿Con quién vives?", "¿Te llevas bien con tu familia?"],
            "amigos":       ["¿Sales seguido?", "¿Tienes un mejor amigo?"],
            "comida":       ["¿Cocinas tú?", "¿Tienes platillo favorito?", "¿Qué no soportas comer?"],
            "salud_mental": ["¿Cómo has estado?", "¿Hay algo que te esté pesando?"],
            "relaciones":   ["¿Cómo van las cosas?", "¿Lo hablaste con alguien?"],
        }
        questions = TOPIC_QUESTIONS.get(topic, [])
        if not questions:
            return None
        if previous_responses:
            unused = [q for q in questions if q not in previous_responses]
            if unused:
                return random.choice(unused)
        return random.choice(questions)


# ============================================================
# DECISION ENGINE v0.8.0
# ============================================================

class DecisionEngine:

    def __init__(self):
        self.analyzer            = TextAnalyzer()
        self.aggression_detector = AggressionDetector()
        self.topic_lock          = TopicLock()

        self.thresholds = {
            "ignore":         -0.2,
            "reveal_secret":  95,
            "hostile_energy": 30
        }

        self.secrets_revealed:  Dict[str, int]  = {}
        self._secrets_date:     Dict[str, date]  = {}  # NUEVO: fecha de último reveal
        self.aggression_count:  Dict[str, int]  = {}
        self.recovery_needed:   Dict[str, int]  = {}
        self.short_streak:      Dict[str, int]  = {}
        self._topic_question_history: Dict[str, list] = {}

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
        display_name: str = "tú",
        emotion_engine=None,     # NUEVO: para acceder a mood_reason e is_night_mode
        profile_manager=None,    # NUEVO: para quote recall
        profile=None,            # NUEVO: para quote recall
    ) -> Dict[str, Any]:

        if profile_modifiers is None:
            profile_modifiers = {}

        name      = display_name
        sentiment = self.analyzer.analyze_sentiment(message)
        keywords  = self.analyzer.extract_keywords(message)
        is_humor  = self.analyzer.is_humor(message)

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
        important_quotes  = profile_modifiers.get("important_quotes", [])
        patience          = profile_modifiers.get("patience", 1.0)
        ignore_adjust     = profile_modifiers.get("ignore_threshold_adjust", 0.0)
        ignore_threshold  = self.thresholds["ignore"] * patience + ignore_adjust
        hostile_threshold = profile_modifiers.get("hostility_threshold", self.thresholds["hostile_energy"])
        empathy_bonus     = profile_modifiers.get("empathy_bonus", 0.0)

        agg_count  = self.aggression_count.get(user_id, 0)
        rec_needed = self.recovery_needed.get(user_id, 0)
        streak     = self.short_streak.get(user_id, 0)
        is_apology = self.analyzer.is_apology(message)

        # NUEVO: reset diario de secretos
        if settings.SECRETS_DAILY_RESET:
            self._daily_secrets_reset(user_id)

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

        # ════════════════════════════════════════════════════
        # PRIORITY RESOLVER
        # ════════════════════════════════════════════════════

        # PRIORIDAD 1 — Identidad
        identity_response = detect_identity_question(message)
        if identity_response:
            return self._return(user_id, message, sentiment,
                                self._inject_name(identity_response, name),
                                emotion, relationship_score, action="identity")

        # PRIORIDAD 2 — Modo noche (respuesta íntima)
        if emotion_engine and emotion_engine.is_night_mode():
            night_resp = self._night_response(emotion.trust, name)
            if night_resp and random.random() < 0.35:
                return self._return(user_id, message, sentiment, night_resp,
                                    emotion, relationship_score, action="night")

        # PRIORIDAD 3 — Ofensa activa
        aggression = self.aggression_detector.detect(message, trust=emotion.trust)
        if aggression["detected"]:
            if not aggression["is_joke"]:
                agg_count += 1
                self.aggression_count[user_id] = agg_count
                self.topic_lock.release(user_id)

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

        # PRIORIDAD 4 — Recovery activo
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

        # PRIORIDAD 5 — Opinión / tema
        if agg_count == 0 and rec_needed == 0:
            opinion = get_opinion(message, name)
            if opinion:
                self.topic_lock.update(user_id, message)
                return self._return(user_id, message, sentiment, opinion,
                                    emotion, relationship_score, action="opinion")

        # PRIORIDAD 6 — Topic activo
        active_topic = self.topic_lock.update(user_id, message)

        # PRIORIDAD 7 — Acción principal
        action         = "respond"
        special_content = None
        secret_blocked  = rec_needed > 0 or agg_count > 0

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
            is_humor=is_humor,
        )

        # PRIORIDAD 8 — Enriquecer
        if action == "respond" and rec_needed == 0:
            response = self._enrich_response(
                response=response,
                user_id=user_id,
                active_topic=active_topic,
                streak=streak,
                message=message,
                sentiment=sentiment,
                emotion=emotion,
                keywords=keywords,
                context=context,
                traits=traits,
                important_quotes=important_quotes,
                emotion_engine=emotion_engine,
            )

        return self._return(user_id, message, sentiment, response,
                            emotion, relationship_score, action=action)

    # ============================================================
    # ENRIQUECIMIENTO
    # ============================================================

    def _enrich_response(
        self,
        response: str,
        user_id: str,
        active_topic: Optional[str],
        streak: int,
        message: str,
        sentiment: float,
        emotion: EmotionalState,
        keywords: list,
        context: dict,
        traits: dict,
        important_quotes: list = None,
        emotion_engine=None,
    ) -> str:
        has_question = "?" in response

        # 7a — Momentum
        if streak >= settings.SHORT_RESPONSE_STREAK_MAX:
            return pick(MOMENTUM_DEPTH_PROMPTS)

        if has_question:
            return response

        # 7b — Quote recall (NUEVO v0.8.0)
        if (
            important_quotes
            and emotion.trust > 60
            and random.random() < settings.QUOTE_RECALL_PROB
        ):
            quote = random.choice(important_quotes)
            frase = random.choice(QUOTE_RECALL_PHRASES).format(quote=quote)
            return f"{response} {frase}"

        # 7c — Topic activo
        if active_topic:
            history = self._topic_question_history.get(user_id, [])
            tq = self.topic_lock.get_topic_question(active_topic, history)
            if tq:
                history.append(tq)
                self._topic_question_history[user_id] = history[-5:]
                return f"{response} {tq}"

        # 7d — Curiosidad general
        if (
            "?" not in message
            and sentiment is not None and sentiment >= 0
            and emotion.trust >= settings.CURIOSITY_TRUST_MIN
            and traits.get("curiosity", 50) > 50
            and random.random() < settings.CURIOSITY_TRIGGER_PROB
        ):
            question = self._contextual_question(keywords, sentiment, context)
            return f"{response} {question}"

        return response

    # ============================================================
    # HELPERS
    # ============================================================

    def _inject_name(self, text: str, name: str) -> str:
        return text.replace("{name}", name)

    def _night_response(self, trust: float, name: str) -> Optional[str]:
        """Genera una respuesta nocturna íntima."""
        lvl = trust_level(trust)
        opciones = NIGHT_RESPONSES.get(lvl, NIGHT_RESPONSES["trust_low"])
        raw = pick(opciones)
        return self._inject_name(raw, name)

    def _daily_secrets_reset(self, user_id: str):
        """FIX: resetea secrets_revealed si cambió el día."""
        today = date.today()
        last_date = self._secrets_date.get(user_id)
        if last_date != today:
            self.secrets_revealed[user_id] = 0
            self._secrets_date[user_id] = today

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
        is_humor: bool = False,
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

        # NUEVO: tono más juguetón si el usuario está en modo humor
        if is_humor and emotion.trust > 50:
            humor_extras = [
                "jeje", "😄", "ja", "qué bueno eso jeje",
            ]
            base = base.rstrip() + f" {random.choice(humor_extras)}"

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
                    context["push_pull"]       = True
                    context["emotional_swing"] = True

        if context["push_pull"]:
            context["repetition_level"] = 0

        return context



        # core/emotion_engine.py
# ============================================================
# SocialBot v0.8.0
# FIX: Indentación rota del archivo original (emotion_engine estaba
#      accidentalmente anidado dentro de _get_secret).
# NUEVO: mood_reason — Sofía sabe POR QUÉ está en cierto estado.
#        Permite respuestas como "todavía pienso en lo que me dijiste".
# NUEVO: Modo noche — energy_decay más suave de noche, tono más íntimo.
# ============================================================

from typing import Optional
from models.state import EmotionalState, Emotion
from models.interaction import Interaction
from core.memory import Memory
from utils.logger import logger
from config import settings
import time
from datetime import datetime

MAX_DELTA_PER_MESSAGE = 3.0


class EmotionEngine:
    """Gestiona estados emocionales por usuario."""

    # Razones internas que Sofía puede referenciar en sus respuestas
    MOOD_REASONS = {
        "aggression":    "alguien fue grosero conmigo",
        "affection":     "alguien fue muy amable",
        "long_silence":  "pasó mucho tiempo sin hablar",
        "good_vibes":    "la conversación estuvo muy buena",
        "repetition":    "siento que la conversación se estancó",
        "recovery":      "estamos arreglando las cosas poco a poco",
    }

    def __init__(self, initial_state: Optional[EmotionalState] = None):
        self.state = initial_state or EmotionalState()
        self.mood_decay = 0.95
        self.last_update_time = time.time()
        # mood_reason por usuario { user_id: str }
        self._mood_reasons: dict = {}

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
            state.energy = self._clamp(state.energy + aggression_impact.get("energy", 0))
            state.trust  = self._clamp(state.trust  + aggression_impact.get("trust",  0))
            # Registrar razón del estado
            self._mood_reasons[interaction.user_id] = self.MOOD_REASONS["aggression"]

        else:
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
                self._mood_reasons[interaction.user_id] = self.MOOD_REASONS["recovery"]

            elif interaction.sentiment > 0.6:
                self._mood_reasons[interaction.user_id] = self.MOOD_REASONS["affection"]
            elif interaction.sentiment > 0.3:
                self._mood_reasons[interaction.user_id] = self.MOOD_REASONS["good_vibes"]

            energy_delta = total_impact * 0.3
            trust_delta  = total_impact * 0.2

            state.energy = self._clamp(state.energy + self._cap_delta(energy_delta))
            state.trust  = self._clamp(state.trust  + self._cap_delta(trust_delta))

        self._update_primary_emotion(state)
        state.last_updated = interaction.timestamp.timestamp()
        return state

    # ==========================================================
    # MOOD REASON — para que Sofía referencie su estado
    # ==========================================================

    def get_mood_reason(self, user_id: str) -> Optional[str]:
        """Retorna la razón del estado emocional actual (o None)."""
        return self._mood_reasons.get(user_id)

    def clear_mood_reason(self, user_id: str):
        self._mood_reasons.pop(user_id, None)

    # ==========================================================
    # MODO NOCHE
    # ==========================================================

    def is_night_mode(self) -> bool:
        """Retorna True si la hora actual está en modo noche."""
        hour = datetime.now().hour
        start = settings.NIGHT_MODE_START_HOUR
        end   = settings.NIGHT_MODE_END_HOUR
        # Maneja el cruce de medianoche (ej: 22-6)
        if start > end:
            return hour >= start or hour < end
        return start <= hour < end

    # ==========================================================
    # LÓGICA INTERNA
    # ==========================================================

    def _cap_delta(self, delta: float) -> float:
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
# SocialBot v0.8.0
# FIX: get_greeting usaba session_count donde debía usar days.
#      "Ya llevamos 47 días" cuando eran 47 sesiones → corregido.
# NUEVO: last_session_tone — Sofía recuerda cómo terminó la conversación.
#        Si el usuario se fue enojado: "La última vez no quedamos muy bien..."
# NUEVO: Saludos según hora del día (modo noche).
# ============================================================

from datetime import datetime
from typing import Optional
from storage.database import Database
from config.sofia_voice import pick
from config import settings
import random


# ============================================================
# SALUDOS CON MEMORIA
# ============================================================

SALUDOS = {
    "nuevo": [
        "¡Holi! Soy Sofía. ¿Cómo estás? 😊",
        "Hola, qué bueno que estás aquí. ¿Cómo te llamas?",
        "¡Oye, hola! Es la primera vez que hablamos, ¿verdad? Cuéntame de ti.",
    ],
    "conocido_sin_temas": [
        "¡Hola! ¿Cómo estás hoy?",
        "Oye, hola. ¿Qué tal tu día?",
        "Holi, ¿cómo vas?",
        "¡Oye! ¿Todo bien por ahí?",
    ],
    "conocido_con_tema": [
        "¡Hola! Oye, la otra vez mencionaste {topic}. ¿Cómo va eso?",
        "Holi 😊 Oye, ¿qué pasó con {topic}?",
        "¡Oye! ¿Cómo te fue con {topic}?",
        "Hola, ¿sigues con lo de {topic}?",
    ],
    # FIX: ahora {days} es el número de DÍAS (variable days), no session_count
    "dias_hablando": [
        "¡Oye! Ya llevamos {days} días hablando, jeje.",
        "Hola 😊 ¿Sabías que ya llevamos {days} días? Qué padre.",
        "Holi. {days} días ya, ¿cómo estás hoy?",
    ],
    # NUEVO v0.8.0 — Saludos de reconciliación
    "reconciliacion": [
        "Hola… la última vez no quedamos muy bien. ¿Estás mejor?",
        "Oye… la otra vez me quedé pensando. ¿Todo ok?",
        "Holi. Espero que hoy sea mejor que la última vez. ¿Cómo estás?",
    ],
    # NUEVO v0.8.0 — Saludos nocturnos
    "noche": [
        "Oye… es tarde. ¿Estás bien?",
        "Mm… ¿sin poder dormir?",
        "Holi. Las horas raras tienen sus propias conversaciones, ¿verdad?",
        "Es tarde. ¿Qué tienes en la cabeza a esta hora?",
    ],
    "madrugada": [
        "Oye… ¿todo bien? Es muy tarde.",
        "Mm… a esta hora la cabeza no para, ¿verdad?",
        "Hola. Pocas personas despiertas a esta hora. ¿Qué pasa?",
    ],
}


class SessionManager:
    def __init__(self, db: Database):
        self.db = db

    # --------------------------------------------------------
    # SALUDO PRINCIPAL
    # --------------------------------------------------------

    def get_greeting(self, user_id: str) -> str:
        """
        Prioridad:
          1. Modo noche / madrugada (hora actual)
          2. Reconciliación si última sesión fue negativa
          3. Días hablando (si son ≥ 3 sesiones)
          4. Tema relevante de la última sesión
          5. Usuario conocido sin temas
          6. Usuario nuevo
        """
        # 1. Modo noche
        night_greeting = self._night_greeting()
        if night_greeting:
            return night_greeting

        session = self.db.load_last_session(user_id)

        if not session:
            return pick(SALUDOS["nuevo"])

        days          = self._days_since(session["date"])
        session_count = session.get("session_count", 1)
        topics        = session.get("topics", [])
        facts         = session.get("important_facts", {})
        last_tone     = session.get("last_session_tone", "neutral")

        # 2. Reconciliación
        if last_tone == "negative":
            return pick(SALUDOS["reconciliacion"])

        # 3. Días hablando (FIX: usamos `days`, no `session_count`)
        if session_count >= 3:
            frase = pick(SALUDOS["dias_hablando"])
            return frase.format(days=days)   # ← FIX: era session_count

        # 4. Tema relevante
        top_topic = self._pick_top_topic(topics, facts)
        if top_topic:
            frase = pick(SALUDOS["conocido_con_tema"])
            return frase.format(topic=top_topic)

        # 5. Conocido sin temas
        return pick(SALUDOS["conocido_sin_temas"])

    # --------------------------------------------------------
    # GUARDAR SESIÓN (incluye tono de cierre)
    # --------------------------------------------------------

    def save_session(self, user_id: str, profile, last_tone: str = "neutral") -> None:
        """
        Guarda resumen de la sesión.
        last_tone: "positive" | "neutral" | "negative"
        """
        last = self.db.load_last_session(user_id)
        session_count = (last["session_count"] + 1) if last else 1

        self.db.save_session(
            user_id=user_id,
            topics=profile.topics,
            important_facts=profile.important_facts,
            session_count=session_count,
            last_session_tone=last_tone,
        )

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------

    def _night_greeting(self) -> Optional[str]:
        """Retorna saludo nocturno según la hora actual."""
        hour = datetime.now().hour
        if 0 <= hour < 5:
            return pick(SALUDOS["madrugada"])
        if hour >= settings.NIGHT_MODE_START_HOUR or hour < settings.NIGHT_MODE_END_HOUR:
            return pick(SALUDOS["noche"])
        return None

    def _days_since(self, date: datetime) -> int:
        delta = datetime.now() - date
        return max(0, delta.days)

    def _pick_top_topic(self, topics: list, facts: dict) -> Optional[str]:
        stopwords = {
            "hola", "bien", "mal", "nada", "algo", "todo",
            "eso", "esto", "aqui", "ahi", "igual", "bueno"
        }

        if facts:
            sorted_facts = sorted(facts.items(), key=lambda x: x[1], reverse=True)
            for fact, weight in sorted_facts:
                if weight >= 2.0:
                    clean = self._clean_fact(fact)
                    if clean:
                        return clean

        for topic in topics:
            if topic.lower() not in stopwords and len(topic) > 3:
                return topic

        return None

    def _clean_fact(self, fact: str) -> str:
        skip_patterns = ["soy ", "tiene ", "es "]
        fact_lower = fact.lower()

        for pattern in skip_patterns:
            if fact_lower.startswith(pattern):
                return ""

        if "gusta" in fact_lower:
            parts = fact_lower.split("gusta")
            if len(parts) > 1:
                topic = parts[1].strip()
                return topic if len(topic) > 2 else ""

        if "estudia" in fact_lower:
            parts = fact_lower.split("estudia")
            if len(parts) > 1:
                return parts[1].strip()

        if "trabaja" in fact_lower:
            parts = fact_lower.split("en")
            if len(parts) > 1:
                return parts[-1].strip()

        return fact


        # core/user_profile_manager.py
# ============================================================
# SocialBot v0.8.0
# NUEVO: _extract_memorable_quote — detecta frases con peso emocional
#        alto y las guarda en profile.important_quotes.
#        Ejemplos: confesiones, reflexiones, cosas personales.
# NUEVO: _daily_secrets_reset — si SECRETS_DAILY_RESET=True, el contador
#        de secretos revelados se resetea automáticamente cada día.
# ============================================================

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


# Patrones que indican una confesión / reflexión personal valiosa
MEMORABLE_PATTERNS = [
    re.compile(r'\b(?:siempre|nunca|jamás)\s+.{10,}', re.IGNORECASE),
    re.compile(r'\b(?:a veces pienso|me pregunto si|tengo miedo de|sueño con|quisiera|ojalá)\s+.{8,}', re.IGNORECASE),
    re.compile(r'\b(?:lo que más me importa|lo que más quiero|lo que más me duele)\s+.{5,}', re.IGNORECASE),
    re.compile(r'\b(?:nadie sabe que|no le he dicho a nadie|te confieso)\s+.{5,}', re.IGNORECASE),
    re.compile(r'\b(?:me arrepiento de|ojala hubiera|si pudiera volver)\s+.{5,}', re.IGNORECASE),
]


class UserProfileManager:
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
        # 1. Decaimiento de hechos
        self._apply_fact_decay(profile, interaction.timestamp)

        # 2. Contadores
        profile.interaction_count += 1
        profile.last_seen = interaction.timestamp
        if not profile.first_seen:
            profile.first_seen = interaction.timestamp

        # 3. Estilo comunicación
        style = self._detect_communication_style(interaction.message)
        if style:
            profile.communication_style = style

        # 4. Temas
        keywords = self.analyzer.extract_keywords(interaction.message, max_words=3)
        current_topics = set(profile.topics)
        current_topics.update(keywords)
        profile.topics = list(current_topics)[:10]

        # 5. Hechos importantes
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

        # 6. NUEVO v0.8.0 — Frases memorables
        quote = self._extract_memorable_quote(interaction.message, interaction.sentiment)
        if quote:
            if quote not in profile.important_quotes:
                profile.important_quotes.append(quote)
                # Mantener solo las más recientes
                if len(profile.important_quotes) > settings.MAX_IMPORTANT_QUOTES:
                    profile.important_quotes = profile.important_quotes[-settings.MAX_IMPORTANT_QUOTES:]

        # 7. Sistema de daño relacional
        if interaction.sentiment is not None:
            if interaction.sentiment < -0.3:
                damage_increment = abs(interaction.sentiment) * 2
                profile.relationship_damage += damage_increment

            repair_mult = self.analyzer.get_repair_multiplier(interaction.message)
            if repair_mult > 1.0 and interaction.sentiment >= 0:
                trust = profile.emotional_state.trust
                if trust > 70:
                    trust_factor = 1.2
                elif trust < 40:
                    trust_factor = 0.5
                else:
                    trust_factor = 1.0

                reduction = repair_mult * 1.5 * trust_factor
                profile.relationship_damage = max(0.0, profile.relationship_damage - reduction)

        # 8. Evolución de personalidad
        if interaction.sentiment is not None:
            if interaction.sentiment > 0.5:
                profile.personality_offsets["attachment"] += 0.5
            elif interaction.sentiment < -0.5:
                profile.personality_offsets["boundary_strength"] += 0.8
                profile.personality_offsets["attachment"] -= 0.5

        for k in profile.personality_offsets:
            profile.personality_offsets[k] = max(-30.0, min(30.0, profile.personality_offsets[k]))

        # Guardar
        self.db.save_user_profile(profile)
        self.cache[profile.user_id] = profile

    # ------------------------------------------------------------
    # NUEVO v0.8.0 — Extracción de frases memorables
    # ------------------------------------------------------------

    def _extract_memorable_quote(self, message: str, sentiment: Optional[float]) -> Optional[str]:
        """
        Detecta si el mensaje contiene una frase personal/confesión memorable.
        Solo guarda frases largas suficientes (≥ MIN_LENGTH) con sentimiento neutro/alto.
        """
        if len(message) < settings.QUOTE_MIN_LENGTH:
            return None

        # Solo mensajes con sentimiento relevante (no completamente neutros)
        if sentiment is not None and abs(sentiment) < 0.2:
            return None

        msg_clean = message.strip()

        for pattern in MEMORABLE_PATTERNS:
            match = pattern.search(msg_clean)
            if match:
                quote = match.group(0).strip()
                # Limpiar y recortar si es muy larga
                if len(quote) > 120:
                    quote = quote[:120].rsplit(' ', 1)[0] + "…"
                return quote

        return None

    def get_random_quote(self, profile: UserProfile) -> Optional[str]:
        """Retorna una frase memorable aleatoria del usuario (para que Sofía la cite)."""
        if not profile.important_quotes:
            return None
        import random
        return random.choice(profile.important_quotes)

    # ------------------------------------------------------------
    # DECAY
    # ------------------------------------------------------------

    def _apply_fact_decay(self, profile: UserProfile, current_time: datetime):
        if not profile.last_seen:
            return

        days_passed = max(0, (current_time - profile.last_seen).total_seconds() / 86400)
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
    # ESTILO DE COMUNICACIÓN
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
            effective_traits[k] = max(0.0, min(100.0, base + offset))

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
            "important_facts": top_facts,
            "important_quotes": profile.important_quotes,  # NUEVO
        }

        if profile.interaction_count > 10 and profile.emotional_state.trust > 70:
            modifiers["empathy_bonus"] += 0.2
            modifiers["hostility_threshold"] = 10.0

        if profile.emotional_state.trust < 30:
            modifiers["empathy_bonus"] -= 0.1
            modifiers["hostility_threshold"] = 30.0

        damage = profile.relationship_damage

        if damage > 5:
            modifiers["hostility_threshold"] = 25.0
            modifiers["empathy_bonus"] -= 0.2
            modifiers["ignore_threshold_adjust"] = 0.2
        elif damage > 2:
            modifiers["hostility_threshold"] = 22.0
            modifiers["empathy_bonus"] -= 0.1
            modifiers["ignore_threshold_adjust"] = 0.1

        boundary    = effective_traits.get("boundary_strength", 70)
        sensitivity = effective_traits.get("sensitivity", 50)
        depth       = effective_traits.get("depth", 65)

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


        # models/user_profile.py
# ============================================================
# SocialBot v0.8.0
# NUEVO: important_quotes — lista de frases memorables del usuario.
#        Sofía puede citarlas: "Oye, una vez dijiste que..."
# ============================================================

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

    # Desviación respecto al núcleo de personalidad
    personality_offsets: Dict[str, float] = field(
        default_factory=lambda: {k: 0.0 for k in RELATIONAL_TRAIT_KEYS}
    )

    # Hechos importantes (memoria selectiva ponderada)
    important_facts: Dict[str, float] = field(default_factory=dict)

    # Daño relacional acumulado
    relationship_damage: float = 0.0

    # NUEVO v0.8.0 — Frases memorables del usuario
    # Lista de strings: las mejores/más reveladoras cosas que dijo
    important_quotes: List[str] = field(default_factory=list)

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
            "relationship_damage": self.relationship_damage,
            "important_quotes": self.important_quotes,  # NUEVO
        }

    @classmethod
    def from_dict(cls, data: dict):
        from models.state import EmotionalState, Emotion

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

        relationship_damage = data.get("relationship_damage", 0.0)

        # NUEVO: cargar important_quotes (retrocompatible)
        important_quotes = data.get("important_quotes", [])
        if not isinstance(important_quotes, list):
            important_quotes = []

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
            relationship_damage=relationship_damage,
            important_quotes=important_quotes,
        )


        # storage/database.py
# ============================================================
# SocialBot v0.8.0
# NUEVO: Columna important_quotes en user_profiles.
# NUEVO: Columna last_session_tone en sessions.
# Ambos retrocompatibles con ALTER TABLE IF NOT EXISTS.
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
    # INIT
    # --------------------------------------------------

    def _init_db(self):
        Path("data").mkdir(exist_ok=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()

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

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emotional_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    emotion TEXT,
                    energy REAL,
                    trust REAL,
                    last_updated TEXT
                )
            """)

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
                    relationship_damage REAL DEFAULT 0.0,
                    important_quotes TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    session_count INTEGER DEFAULT 1,
                    topics TEXT,
                    important_facts TEXT,
                    last_session_tone TEXT DEFAULT 'neutral'
                )
            """)

            conn.commit()

            # Migraciones para DBs existentes
            migrations = [
                "ALTER TABLE user_profiles ADD COLUMN relationship_damage REAL DEFAULT 0.0",
                "ALTER TABLE user_profiles ADD COLUMN important_quotes TEXT",    # NUEVO
                "ALTER TABLE sessions ADD COLUMN last_session_tone TEXT DEFAULT 'neutral'",  # NUEVO
            ]
            for migration in migrations:
                try:
                    cursor.execute(migration)
                    conn.commit()
                except sqlite3.OperationalError:
                    pass  # columna ya existe

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
            quotes_json  = json.dumps(profile.important_quotes) if profile.important_quotes else None  # NUEVO

            cursor.execute("""
                INSERT OR REPLACE INTO user_profiles
                (user_id, emotional_state, interaction_count,
                 communication_style, first_seen, last_seen,
                 topics, personality_traits, important_facts,
                 relationship_damage, important_quotes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                profile.relationship_damage,
                quotes_json,
            ))
            conn.commit()

    def load_user_profile(self, user_id: str) -> Optional[UserProfile]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, emotional_state, interaction_count,
                       communication_style, first_seen, last_seen,
                       topics, personality_traits, important_facts,
                       relationship_damage, important_quotes
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
            quotes_data          = json.loads(row[10]) if row[10] else []  # NUEVO

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
                "relationship_damage": relationship_damage,
                "important_quotes": quotes_data,
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
    # SESSIONS
    # --------------------------------------------------

    def save_session(
        self,
        user_id: str,
        topics: List[str],
        important_facts: dict,
        session_count: int,
        last_session_tone: str = "neutral",   # NUEVO
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sessions
                (user_id, date, session_count, topics, important_facts, last_session_tone)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                datetime.now().isoformat(),
                session_count,
                ",".join(topics[:10]) if topics else "",
                json.dumps(important_facts) if important_facts else "{}",
                last_session_tone,
            ))
            conn.commit()

    def load_last_session(self, user_id: str) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, session_count, topics, important_facts, last_session_tone
                FROM sessions WHERE user_id = ?
            """, (user_id,))

            row = cursor.fetchone()
            if not row:
                return None

            topics = [t.strip() for t in row[2].split(",") if t.strip()] if row[2] else []
            facts  = json.loads(row[3]) if row[3] else {}
            tone   = row[4] if row[4] else "neutral"  # NUEVO

            return {
                "date":               datetime.fromisoformat(row[0]),
                "session_count":      row[1],
                "topics":             topics,
                "important_facts":    facts,
                "last_session_tone":  tone,
            }


            # utils/aggression_detector.py
# ============================================================
# SocialBot v0.8.0
# FIX CRÍTICO: Uso de word boundaries (re.search con \b) en lugar de
#   `phrase in msg_norm` — antes "calla" matcheaba en "caballero",
#   "calle", etc. provocando falsos positivos graves.
# NUEVO: Reducción de impacto si el usuario está en modo humor.
# ============================================================

import re
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
    "leve":  {"energy": -8.0,  "trust": -6.0,  "damage": 1.0},
    "medio": {"energy": -15.0, "trust": -12.0, "damage": 2.5},
    "alto":  {"energy": -25.0, "trust": -18.0, "damage": 4.0},
}

JOKE_INDICATORS = {"jaja", "jeje", "jajaja", "jejeje", "lol", "xd", ":v", "😂", "🤣"}


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFD", text)
    return nfkd.encode("ascii", "ignore").decode("utf-8").lower()


def _match_phrase(phrase: str, text_norm: str) -> bool:
    """
    FIX CRÍTICO: Usa word boundaries para palabras simples.
    Para frases multi-palabra usa búsqueda de subcadena (más natural).
    Antes: `phrase in text_norm` → "calla" matcheaba en "caballero".
    """
    if " " in phrase:
        # Frase multi-palabra: subcadena es suficiente
        return phrase in text_norm
    else:
        # Palabra simple: respetar boundaries
        pattern = r'\b' + re.escape(phrase) + r'\b'
        return bool(re.search(pattern, text_norm))


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
            "level":     str | None,
            "impact":    dict | None,
            "is_joke":   bool,
          }
        """
        msg_norm  = _normalize(message)
        msg_lower = message.lower()
        is_joke   = any(ind in msg_lower for ind in JOKE_INDICATORS)

        for level in ("alto", "medio", "leve"):
            for phrase in INSULT_LEVELS[level]:
                if _match_phrase(phrase, msg_norm):        # ← FIX aplicado
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
# SocialBot v0.8.0
# FIX 1: positive_words/negative_words separados en palabras simples
#         y positive_phrases/negative_phrases para frases multi-palabra.
#         Antes "te quiero" nunca matcheaba porque el loop era por palabra.
# FIX 2: Soporte para backend pysentimiento (modelo IA en español).
#         Configurable en settings.SENTIMENT_BACKEND.
# NUEVO:  Detección de humor general (no solo agresivo).
# ============================================================

import re
import unicodedata
from typing import List, Optional
from config import settings


class TextAnalyzer:
    """Analizador de texto con soporte para dos backends de sentimiento."""

    def __init__(self):
        # ── Palabras simples (1 token) ────────────────────────
        self.positive_words = {
            "gracias", "genial", "excelente", "perfecto",
            "feliz", "alegre", "maravilloso", "bien",
            "buen", "amo", "quiero", "adoro", "bueno",
            "helpful", "thanks", "good", "great",
        }

        self.negative_words = {
            "mal", "peor", "odio", "estupido", "tonto", "feo",
            "horrible", "terrible", "asco", "imbecil", "idiota",
            "hate", "bad", "stupid", "odias", "detesto", "aborrezco",
        }

        # ── Frases multi-palabra (FIX: antes estaban en positive_words) ──
        self.positive_phrases = [
            "te quiero", "te amo", "muchas gracias", "me alegra",
            "me gusta", "me encanta", "que padre", "eres genial",
            "me importas", "eres importante", "te adoro",
        ]

        self.negative_phrases = [
            "no sirves", "eres un fracaso", "me cae mal",
            "no me gustas", "me haces enojar",
        ]

        self.intensifiers = {
            "muy", "mucho", "bastante", "demasiado",
            "super", "really", "very",
        }

        self.apology_phrases = [
            "perdon", "lo siento", "disculpa", "perdona",
            "sorry", "me equivoque", "fue mi culpa", "no quise",
        ]

        self.affection_phrases = [
            "te quiero", "te amo", "aprecio", "gracias por",
            "me importas", "eres importante", "te adoro",
        ]

        # ── Humor general (NUEVO) ─────────────────────────────
        self.humor_indicators = {
            "jaja", "jeje", "lol", "xd", "jajaja", "haha",
            "😂", "🤣", "💀", ":v", "jiji",
        }

        # ── Cache para pysentimiento ──────────────────────────
        self._pysentimiento_analyzer = None
        self._backend = settings.SENTIMENT_BACKEND

        if self._backend == "pysentimiento":
            self._load_pysentimiento()

    def _load_pysentimiento(self):
        """Intenta cargar pysentimiento; si falla, cae al backend básico."""
        try:
            from pysentimiento import create_analyzer
            self._pysentimiento_analyzer = create_analyzer(
                task="sentiment", lang="es"
            )
        except ImportError:
            self._backend = "basic"

    # ---------------------------
    # NORMALIZACIÓN
    # ---------------------------

    def _normalize(self, text: str) -> str:
        """Quita tildes y convierte a minúsculas."""
        nfkd = unicodedata.normalize('NFD', text)
        without_accents = nfkd.encode('ascii', 'ignore').decode('utf-8')
        return without_accents.lower()

    # ---------------------------
    # SENTIMIENTO
    # ---------------------------

    def analyze_sentiment(self, text: str) -> float:
        """
        Retorna valor entre -1 (muy negativo) y 1 (muy positivo).
        Usa pysentimiento si está disponible, de lo contrario el método básico.
        """
        if self._backend == "pysentimiento" and self._pysentimiento_analyzer:
            return self._sentiment_pysentimiento(text)
        return self._sentiment_basic(text)

    def _sentiment_pysentimiento(self, text: str) -> float:
        """Backend IA — más preciso con sarcasmo y contexto."""
        try:
            result = self._pysentimiento_analyzer.predict(text)
            output = result.output  # "POS", "NEG", "NEU"
            probas = result.probas  # {"POS": 0.9, "NEG": 0.05, "NEU": 0.05}
            if output == "POS":
                return probas.get("POS", 0.5)
            elif output == "NEG":
                return -probas.get("NEG", 0.5)
            else:
                return 0.0
        except Exception:
            return self._sentiment_basic(text)

    def _sentiment_basic(self, text: str) -> float:
        """
        Backend básico — palabras clave.
        FIX: ahora revisa frases multi-palabra ANTES del loop por tokens.
        """
        text_normalized = self._normalize(text)
        negation_words  = {"no", "nunca", "jamas", "not", "never"}

        score       = 0.0
        found_words = 0

        # 1. Frases positivas multi-palabra
        for phrase in self.positive_phrases:
            if phrase in text_normalized:
                score += 1.0
                found_words += 1

        # 2. Frases negativas multi-palabra
        for phrase in self.negative_phrases:
            if phrase in text_normalized:
                score -= 1.0
                found_words += 1

        # 3. Palabras simples con manejo de negación e intensificadores
        words  = text_normalized.split()
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
    # HUMOR
    # ---------------------------

    def is_humor(self, text: str) -> bool:
        """Detecta si el mensaje tiene tono de humor general."""
        text_lower = text.lower()
        return any(ind in text_lower for ind in self.humor_indicators)

    # ---------------------------
    # PALABRAS CLAVE
    # ---------------------------

    def extract_keywords(self, text: str, max_words: int = 5) -> List[str]:
        """Extrae palabras clave normalizadas (sin tildes)."""
        normalized = self._normalize(text)
        words = re.findall(r'\b\w+\b', normalized)

        stopwords = {
            "de", "la", "que", "el", "en", "y", "a", "los",
            "del", "se", "las", "por", "un", "para", "con",
            "no", "una", "su", "al", "lo", "como", "mas",
            "pero", "sus", "le", "ya", "o", "fue", "este",
            "si", "mi", "hoy",
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
# SocialBot v0.8.0
# CAMBIOS:
#   - Se pasan emotion_engine, profile y profile_manager a decide_response
#     para habilitar mood_reason, quote recall y modo noche.
#   - save_session incluye last_session_tone calculado desde el estado.
#   - !reset también limpia _secrets_date.
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
    display_name = message.author.display_name

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
        display_name=display_name,
        emotion_engine=emotion_engine,     # NUEVO
        profile_manager=profile_manager,   # NUEVO
        profile=profile,                   # NUEVO
    )

    interaction       = decision_result["interaction"]
    repair_multiplier = decision.analyzer.get_repair_multiplier(message)

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
    decision._secrets_date.pop(user_id, None)          # NUEVO
    decision._topic_question_history.pop(user_id, None)
    await ctx.send("🔄 Contadores reseteados.")


@bot.command(name="estado")
async def estado_cmd(ctx):
    """!estado — muestra el estado emocional actual de Sofía para este usuario (debug)"""
    user_id = str(ctx.author.id)
    profile = await profile_manager.get_or_create_profile(user_id)
    e = profile.emotional_state
    mood_reason = emotion_engine.get_mood_reason(user_id) or "sin razón particular"
    quotes_count = len(profile.important_quotes)
    night = "🌙 sí" if emotion_engine.is_night_mode() else "☀️ no"

    await ctx.send(
        f"**Estado de Sofía contigo:**\n"
        f"Emoción: `{e.primary_emotion.value}` | Energía: `{e.energy:.1f}` | Confianza: `{e.trust:.1f}`\n"
        f"Razón del estado: `{mood_reason}`\n"
        f"Frases memorables guardadas: `{quotes_count}`\n"
        f"Modo noche: {night}\n"
        f"Daño relacional: `{profile.relationship_damage:.2f}`"
    )


# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    if not TOKEN:
        print("❌ No encontré el token. Crea un .env con DISCORD_TOKEN=tu_token")
    else:
        bot.run(TOKEN)


        
