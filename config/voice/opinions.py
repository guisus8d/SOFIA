# config/voice/opinions.py
# ============================================================
# Opiniones contextuales de Sofía + TopicLock + get_opinion.
# ============================================================

import random
from typing import Optional, Dict
from config.voice._base import _normalize, pick


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


TOPIC_ALIASES = {
    "me gusta dibujar":          "dibujar",
    "empece a dibujar":          "dibujar",
    "dibujo mucho":              "dibujar",
    "dibujo personajes":         "personajes",
    "creo personajes":           "personajes",
    "invento personajes":        "personajes",
    "hago ilustraciones":        "ilustracion",
    "pinto acuarelas":           "acuarela",
    "arte digital":              "digital",
    "hago arte":                 "arte",
    "toco guitarra":             "guitarra",
    "toco el piano":             "piano",
    "toco piano":                "piano",
    "toco bateria":              "bateria",
    "toco la bateria":           "bateria",
    "toco bajo":                 "bajo",
    "toco violin":               "violin",
    "toco el violin":            "violin",
    "estoy aprendiendo guitarra":"guitarra",
    "aprendiendo piano":         "piano",
    "compongo canciones":        "componer",
    "escribo canciones":         "componer",
    "hago musica":               "musica",
    "me gusta cantar":           "cantar",
    "canto":                     "cantar",
    "juego mucho minecraft":     "minecraft",
    "juego minecraft":           "minecraft",
    "construyo mundos":          "minecraft",
    "juego fortnite":            "fortnite",
    "juego valorant":            "valorant",
    "juego roblox":              "roblox",
    "me gustan los videojuegos": "videojuegos",
    "juego videojuegos":         "videojuegos",
    "juego mucho":               "videojuegos",
    "me gusta cocinar":          "cocinar",
    "cocino seguido":            "cocinar",
    "hago reposteria":           "reposteria",
    "tomo mucho cafe":           "cafe",
    "tomo cafe":                 "cafe",
    "voy al gimnasio":           "gimnasio",
    "voy al gym":                "gym",
    "entreno seguido":           "gimnasio",
    "salgo a correr":            "correr",
    "corro":                     "correr",
    "juego futbol":              "futbol",
    "me gusta el futbol":        "futbol",
    "aprendo python":            "python",
    "programo en python":        "python",
    "estudio programacion":      "programacion",
    "aprendo a programar":       "programar",
    "estudio en la uni":         "universidad",
    "estoy en la universidad":   "universidad",
    "tengo perro":               "perro",
    "tengo un perro":            "perro",
    "tengo gato":                "gato",
    "tengo un gato":             "gato",
    "me gusta leer":             "leer",
    "leo mucho":                 "leer",
    "leo libros":                "leer",
}


class TopicLock:
    """
    Mantiene el tema activo por usuario.
    - Cuando el usuario continúa el tema → pregunta de seguimiento.
    - Cuando cambia de tema → comentario de transición.
    """

    TOPIC_NAMES: Dict[str, str] = {
        "dibujo": "el dibujo", "dibujar": "el dibujo", "pintura": "la pintura",
        "musica": "la música", "guitarra": "la guitarra", "piano": "el piano",
        "bateria": "la batería", "bajo": "el bajo", "violin": "el violín",
        "componer": "la composición", "cantar": "el canto",
        "escritura": "la escritura", "escribir": "la escritura",
        "fotografia": "la fotografía", "foto": "la fotografía",
        "programacion": "la programación", "programar": "la programación",
        "python": "Python", "javascript": "JavaScript",
        "videojuegos": "los videojuegos", "minecraft": "Minecraft",
        "fortnite": "Fortnite", "valorant": "Valorant",
        "anime": "el anime", "manga": "el manga",
        "peliculas": "las películas", "series": "las series",
        "libros": "los libros", "leer": "la lectura",
        "futbol": "el fútbol", "deportes": "los deportes",
        "gimnasio": "el gimnasio", "gym": "el gym", "correr": "el running",
        "escuela": "la escuela", "universidad": "la uni",
        "trabajo": "el trabajo", "mascotas": "las mascotas",
        "perro": "tu perro", "gato": "tu gato",
    }

    TOPIC_CHANGE_COMMENTS = [
        "Oye, antes hablábamos de {anterior} y ahora me dices lo de {nuevo}. ¿Cómo pasaste de uno al otro?",
        "Mm… curioso, pasamos de {anterior} a {nuevo}. Me gusta ese salto.",
        "Jeje, antes {anterior} y ahora {nuevo}. ¿Qué onda con ese cambio?",
        "De {anterior} a {nuevo} en un mensaje. ¿Qué pasó en el medio?",
        "Oye, ¿ya se te fue lo de {anterior}? Ahora me hablas de {nuevo}.",
    ]

    def __init__(self):
        self._state: Dict[str, dict] = {}

    def _detect_topic(self, message: str) -> Optional[str]:
        msg = _normalize(message)
        for alias, topic in TOPIC_ALIASES.items():
            if _normalize(alias) in msg:
                return topic
        for keyword in OPINIONES:
            if keyword in msg:
                return keyword
        return None

    def _topic_name(self, topic: str) -> str:
        return self.TOPIC_NAMES.get(topic, topic)

    def update(self, user_id: str, message: str):
        new_topic     = self._detect_topic(message)
        state         = self._state.get(user_id, {})
        current_topic = state.get("topic")
        topic_changed = False
        prev_topic    = None

        if new_topic:
            if current_topic and current_topic != new_topic:
                topic_changed = True
                prev_topic    = current_topic
            self._state[user_id] = {"topic": new_topic, "followup_index": 0, "responses": []}
        elif current_topic:
            new_topic = current_topic

        return new_topic, topic_changed, prev_topic

    def get_active(self, user_id: str) -> Optional[str]:
        return self._state.get(user_id, {}).get("topic")

    def get_followup(self, user_id: str) -> Optional[str]:
        state = self._state.get(user_id, {})
        topic = state.get("topic")
        if not topic:
            return None
        prev = state.get("responses", [])
        q    = self.get_topic_question(topic, previous_responses=prev)
        if q:
            prev.append(q)
            state["responses"] = prev
        return q

    def release(self, user_id: str):
        self._state.pop(user_id, None)

    def topic_change_comment(self, prev_topic: str, new_topic: str) -> str:
        anterior = self._topic_name(prev_topic)
        nuevo    = self._topic_name(new_topic)
        frase    = random.choice(self.TOPIC_CHANGE_COMMENTS)
        result   = frase.format(anterior=anterior, nuevo=nuevo)
        result   = result.replace(" de el ", " del ")
        result   = result.replace(" del el ", " del ")
        result   = result.replace(" de la la ", " de la ")
        result   = result.replace(" a el ", " al ")
        result   = result.replace(" al el ", " al ")
        return result

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


# Instancia global
_topic_lock = TopicLock()


def get_opinion(message: str, name: str, user_id: str = None) -> Optional[str]:
    """
    Detección en dos pasos + TopicLock con cambio de tema.
    """
    msg = _normalize(message)

    _GASLIGHTING_PATTERNS = [
        "todo lo que dices es mentira", "solo ejecutas codigo", "solo ejecutas",
        "no eres real", "no tienes sentimientos", "no sientes nada",
        "solo procesas", "eres una mentira", "finges que",
        "todo es mentira", "nada de lo que dices",
    ]
    if any(p in msg for p in _GASLIGHTING_PATTERNS):
        return None

    _ACTIVITY_REPORT_PREFIXES = [
        "hoy fui", "fui al", "fui a", "hoy estuve", "estuve en",
        "ayer fui", "acabo de ir", "vine del", "vine de",
        "acabe de", "acabé de", "llegue de", "llegué de",
    ]
    if any(msg.startswith(_normalize(p)) for p in _ACTIVITY_REPORT_PREFIXES):
        return None

    active_topic  = None
    topic_changed = False
    prev_topic    = None

    if user_id is not None:
        active_topic, topic_changed, prev_topic = _topic_lock.update(user_id, message)

    matched_opinion = None
    for alias, topic_key in TOPIC_ALIASES.items():
        if _normalize(alias) in msg:
            if topic_key in OPINIONES:
                opinion, pregunta = OPINIONES[topic_key]
                matched_opinion = f"{opinion} {pregunta}, {name}?"
                break

    if matched_opinion is None:
        for keyword, (opinion, pregunta) in OPINIONES.items():
            if keyword in msg:
                matched_opinion = f"{opinion} {pregunta}, {name}?"
                break

    if matched_opinion is not None:
        if topic_changed and prev_topic:
            comentario = _topic_lock.topic_change_comment(prev_topic, active_topic)
            return f"{comentario} {matched_opinion}"
        return matched_opinion

    if user_id is not None and active_topic:
        followup = _topic_lock.get_followup(user_id)
        if followup:
            return followup

    return None