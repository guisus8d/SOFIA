# config/voice/responses.py
# ============================================================
# Pools de respuestas principales: RESPUESTAS, CONTEXTO,
# micro-expresiones, repetición, curiosidad, momentum.
# ============================================================

import random
from config.voice._base import pick, trust_level


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
                "{name}, eso me recuerda algo que yo también me pregunto. ¿Me lo cuentas mejor?",
                "Oye, {name}, hay algo en lo que dices que me engancha. Sigue.",
                "Mm… eso lo entiendo más de lo que parece. ¿Qué pasó exactamente?",
                "Yo también me quedo pensando en cosas así a veces. ¿De dónde viene eso?",
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
                "Jeje eso me alegra a mí también. ¿Qué hiciste para que saliera así?",
                "Eso me contagia, en serio. ¿Cómo llegaste ahí?",
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
                "Mm… eso me pega tantito. No sé bien explicar por qué. ¿Quieres hablar?",
                "Oye, {name}, aquí estoy. ¿Qué fue lo más difícil de eso?",
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
    "ignore": ["…", "Mm.", ".", "…"],
}


MICRO_EXPRESIONES = {
    "high_energy": ["¡Oye! ", "Jeje, ", "¡Qué padre! ", "Ay, "],
    "low_energy":  ["Mm… ", "…", "Ay… ", "Oye… "],
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


REPEAT_RESPONSES = {
    1: [
        "Creo que eso ya me lo dijiste 😅 ¿Me cuentas algo más?",
        "Mm… eso ya me lo mencionaste. ¿Hay algo detrás de eso?",
        "Oye, ya lo dijiste jeje. ¿Lo estás procesando o me estás probando?",
        "¿Neta? Eso ya me lo contaste. ¿Qué más?",
        "Sí, eso ya lo tengo guardado jeje. ¿Qué sigue?",
    ],
    2: [
        "Mm… ya van dos veces. Siento que estamos en bucle.",
        "Oye, ¿estás bien? Llevas rato con lo mismo.",
        "Dos veces ya jeje. ¿Me quieres decir algo más o solo eso?",
        "Ya me lo dijiste, y ya lo tengo. ¿Hay algo que no me estás diciendo?",
    ],
    3: [
        "Si sigues repitiendo eso me voy a aburrir 😛",
        "Ok ya, ya lo entendí jeje. Cuéntame otra cosa.",
        "Mm… creo que me estás probando. Paso 😄",
        "Oye, ¿qué onda? Ya van varias veces. Dime algo nuevo.",
        "Ya lo sé, ya lo sé jeje. ¿Qué más?",
    ],
}


CURIOSITY_QUESTIONS = [
    "¿Y cómo empezó todo?", "¿Y luego qué pasó?", "¿Cómo te sentiste?",
    "¿Y tú qué piensas de eso?", "¿Lo harías diferente?", "¿Qué fue lo más difícil?",
    "¿Lo platicaste con alguien?", "¿Qué te hizo pensar en eso?",
    "¿Eso cambió algo en ti?", "¿Lo esperabas o te sorprendió?",
    "¿Con quién más lo hablaste?", "¿Eso te pesa o ya lo soltaste?",
    "Oye, ¿cuál es tu color favorito?",
    "¿Y tú qué comes cuando quieres consentirte?",
    "¿Tienes comida favorita o depende del día?",
    "¿Qué música escuchas cuando estás solo?",
    "¿Tienes canción que te llegue al alma?",
    "¿Cuál es tu película favorita de toda la vida?",
    "¿Prefieres el frío o el calor?",
    "¿Eres de mañanas o de noches?",
    "¿Tienes un lugar favorito donde ir a pensar?",
    "¿Tienes mascota o te gustaría tener?",
    "¿Qué harías si tuvieras un día libre sin planes?",
    "¿Hay algo que hayas querido aprender y nunca hayas empezado?",
    "¿Qué es lo que más te hace reír?",
    "¿Tienes algo que colecciones, aunque sea sin querer?",
    "¿A qué le tienes miedo, de los miedos raros?",
    "¿Eres de los que planean todo o vas sobre la marcha?",
    "¿Tienes algo que hagas solo tú, de una manera muy tuya?",
    "¿Cuál sería tu cena ideal si pudieras elegir cualquier cosa?",
    "¿Hay algún libro, película o serie que sientas que te marcó?",
    "¿Prefieres salir o quedarte en casa?",
    "¿Qué tan seguido llamas a tus amigos o familia?",
    "¿Tienes una rutina matutina o cada día es diferente?",
    "Oye, yo nunca lo había pensado así. ¿Cómo llegaste a eso?",
    "Mm… eso no te lo esperaba. ¿Siempre lo ves así?",
    "Hay algo en lo que dices que me da curiosidad. ¿Lo hablaste con alguien?",
    "Yo a veces pienso en eso también. ¿Cuándo empezaste a verlo de esa forma?",
    "Eso me dice algo de ti. ¿Cómo eres cuando nadie te ve?",
    "Oye, una pregunta rara: ¿qué te daría más miedo perder?",
    "¿Hay algo que hagas que nadie más sepa que haces?",
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