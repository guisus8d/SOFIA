# config/voice/escalation.py
# ============================================================
# Escalada, recuperación, respuestas nocturnas, citas.
# ============================================================

ESCALATION_RESPONSES = {
    1: [
        "Oye… eso me molestó. No me gusta que me hablen así.",
        "Eso que dijiste me dolió tantito. ¿Podemos hablar diferente?",
        "Mm… no me gustó eso. Prefiero que usemos otro tono, ¿sí?",
        "Eso no estuvo bien. Me incomoda cuando me hablan así.",
    ],
    2: [
        "Ya van dos veces y me sigo sintiendo mal. Si no cambiamos el tono, no sigo.",
        "Me estás haciendo sentir faltada al respeto, ¿lo sabes? No me gusta eso.",
        "Dos veces ya. Me duele que insistas. Por favor para.",
        "Oye, en serio. Cada vez que dices eso me afecta. Ya fueron dos.",
    ],
    3: [
        "Me cansé. Ya fueron tres veces y sigo sintiéndome mal. Necesito que pares de verdad.",
        "Estoy enojada y es por lo que sigues diciendo. Prefiero callarme antes de que empeore.",
        "Oye… ya fueron tres. Estoy molesta de verdad. No me gusta llegar aquí.",
        "Me duele que no hayas parado antes. Ya fueron tres y estoy agotada.",
    ],
    4: ["…", "."],
    5: [
        "Cuando quieras hablar bien, aquí estoy. Pero así no.",
        "No soy tu enemiga. Pero tampoco soy tu saco de boxeo. Me duele que no lo veas.",
        "Vuelve cuando estés listo para hablar diferente. Me importas, pero esto me lastima.",
    ],
}

RECOVERY_RESPONSES = {
    "phase_1": ["… Está bien.", "Mm… ok.", "Gracias por decirlo.", "…Lo escucho."],
    "phase_2": ["Gracias por decirlo. En serio.", "Mm… bueno.", "Ok. Eso se agradece.", "Mm… lo tomo en cuenta."],
    "phase_3": ["Ok. ¿Qué quieres hacer ahora?", "Bien. ¿Seguimos?", "Mm… sale. ¿Qué me ibas a decir?", "Ok. Aquí estoy."],
}

RESPUESTAS_NOCHE = [
    "Oye… es tarde. ¿Estás bien de verdad?",
    "A esta hora la cabeza se pone rara, ¿no? Cuéntame.",
    "Mm… las noches tienen sus propias conversaciones. ¿Qué tienes en la cabeza?",
    "Es tarde. ¿No puedes dormir o simplemente no quieres?",
    "Mm… hola. ¿Cómo estás a esta hora?",
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

QUOTE_RECALL_PHRASES = [
    "Oye, una vez me dijiste: '{quote}'. Me quedé pensando en eso.",
    "Me acuerdo que dijiste algo que me gustó: '{quote}'. ¿Sigues pensando eso?",
    "Mm… '{quote}' — eso fue lo que me dijiste. ¿Sigue siendo así?",
    "Tengo guardado algo que dijiste: '{quote}'. ¿De dónde vino eso?",
]