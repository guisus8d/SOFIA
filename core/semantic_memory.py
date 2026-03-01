# core/semantic_memory.py
# ============================================================
# SemanticMemory + IntentClassifier
# Extraído de decision_engine.py en v0.13.0
# ============================================================

import random
import unicodedata


class SemanticMemory:
    EXTRACTION_RULES = [
        # ── COMIDAS ──────────────────────────────────────────────
        (["me gusta la pizza", "amo la pizza", "me encanta la pizza"],           "comida_favorita", "pizza"),
        (["me gustan los tacos", "amo los tacos", "me encantan los tacos"],      "comida_favorita", "tacos"),
        (["me gusta el sushi", "amo el sushi", "me encanta el sushi"],           "comida_favorita", "sushi"),
        (["me gusta la hamburguesa", "me gustan las hamburguesas",
          "me encanta la hamburguesa"],                                           "comida_favorita", "hamburguesa"),
        (["me gusta el ramen", "amo el ramen", "me encanta el ramen"],           "comida_favorita", "ramen"),
        (["me gusta la pasta", "amo la pasta", "me encanta la pasta"],           "comida_favorita", "pasta"),

        # ── DEPORTES ─────────────────────────────────────────────
        (["me gusta el futbol", "me encanta el futbol",
          "amo el futbol", "juego futbol"],                                       "deporte_interes", "futbol"),
        (["no tengo equipo", "no tengo equipo de futbol"],                       "futbol_tiene_equipo", "no"),
        (["mi equipo es", "soy del"],                                            "futbol_equipo",   None),
        (["me gusta el basquetbol", "me gusta el basket",
          "me encanta el basket", "juego basket"],                               "deporte_interes", "basquetbol"),
        (["me gusta el tenis", "juego tenis", "me encanta el tenis"],            "deporte_interes", "tenis"),
        (["me gusta nadar", "nado mucho", "me encanta nadar"],                   "deporte_interes", "natacion"),
        (["me gusta correr", "corro mucho", "salgo a correr"],                   "deporte_interes", "running"),
        (["me gusta el gym", "voy al gym", "entreno",
          "me gusta ejercitarme"],                                               "deporte_interes", "gym"),

        # ── MÚSICA — géneros ──────────────────────────────────────
        (["me gusta la musica", "amo la musica",
          "me encanta la musica"],                                               "musica_le_gusta", "si"),
        (["me gusta el rock", "amo el rock", "escucho rock",
          "me encanta el rock"],                                                 "musica_genero",   "rock"),
        (["me gusta el pop", "escucho pop",
          "me encanta el pop"],                                                  "musica_genero",   "pop"),
        (["me gusta el rap", "escucho rap", "me gusta el hiphop",
          "me encanta el rap", "me encanta el hiphop"],                         "musica_genero",   "rap/hiphop"),
        (["me gusta el metal", "escucho metal",
          "me encanta el metal", "amo el metal"],                               "musica_genero",   "metal"),
        (["me gusta el jazz", "escucho jazz",
          "me encanta el jazz"],                                                 "musica_genero",   "jazz"),
        (["me gusta la cumbia", "escucho cumbia",
          "me encanta la cumbia"],                                               "musica_genero",   "cumbia"),
        (["me gusta el reggaeton", "escucho reggaeton",
          "me encanta el reggaeton"],                                            "musica_genero",   "reggaeton"),
        (["me gusta el clasico", "escucho musica clasica",
          "me gusta la musica clasica"],                                         "musica_genero",   "clasica"),

        # ── HOBBIES / ACTIVIDADES ─────────────────────────────────
        (["dibujo mucho", "me gusta dibujar", "amo dibujar",
          "me encanta dibujar", "soy artista", "hago arte"],                    "hobby",           "dibujar"),
        (["me gusta escribir", "escribo mucho", "escribo historias",
          "me encanta escribir", "amo escribir"],                               "hobby",           "escribir"),
        (["me gusta leer", "amo leer", "leo mucho",
          "me encanta leer"],                                                    "hobby",           "leer"),
        (["me gusta cocinar", "cocino mucho", "amo cocinar",
          "me encanta cocinar"],                                                 "hobby",           "cocinar"),
        (["me gusta jugar videojuegos", "juego videojuegos",
          "me gustan los videojuegos", "me encantan los videojuegos",
          "juego mucho"],                                                        "hobby",           "videojuegos"),
        (["me gusta tocar", "toco guitarra", "toco piano",
          "toco bajo", "toco bateria", "toco el piano",
          "toco la guitarra"],                                                   "hobby",           "tocar música"),
        (["me gusta la fotografía", "hago fotografia",
          "me encanta la fotografia"],                                           "hobby",           "fotografia"),
        (["me gusta bailar", "bailo mucho",
          "me encanta bailar"],                                                  "hobby",           "bailar"),

        # ── OCUPACIONES ───────────────────────────────────────────
        (["soy programador", "soy desarrollador", "programo",
          "trabajo en codigo", "trabajo en software",
          "soy dev", "trabajo de programador"],                                 "ocupacion",       "programador"),
        (["soy medico", "soy médico", "soy doctor", "soy doctora",
          "trabajo de medico", "trabajo de médico",
          "estudio medicina"],                                                   "ocupacion",       "médico"),
        (["soy enfermero", "soy enfermera",
          "trabajo de enfermero"],                                               "ocupacion",       "enfermero"),
        (["soy abogado", "soy abogada",
          "trabajo de abogado", "estudio derecho"],                             "ocupacion",       "abogado"),
        (["soy ingeniero", "soy ingeniera",
          "trabajo de ingeniero"],                                               "ocupacion",       "ingeniero"),
        (["soy arquitecto", "soy arquitecta",
          "estudio arquitectura"],                                               "ocupacion",       "arquitecto"),
        (["soy contador", "soy contadora",
          "trabajo de contador"],                                                "ocupacion",       "contador"),
        (["soy psicologo", "soy psicólogo", "soy psicologa",
          "estudio psicologia"],                                                 "ocupacion",       "psicólogo"),
        (["estudio", "soy estudiante",
          "voy a la universidad", "voy a la prepa"],                            "ocupacion",       "estudiante"),
        (["trabajo", "soy trabajador"],                                          "ocupacion",       "trabajador"),
        (["soy diseñador", "soy disenador", "trabajo en diseño",
          "soy diseñadora"],                                                     "ocupacion",       "diseñador"),
        (["soy maestro", "soy profesor", "enseño",
          "soy maestra", "soy profesora"],                                      "ocupacion",       "maestro"),
        (["soy chef", "trabajo de chef",
          "trabajo en cocina"],                                                  "ocupacion",       "chef"),
        (["soy vendedor", "soy vendedora",
          "trabajo en ventas"],                                                  "ocupacion",       "vendedor"),

        # ── ESTADOS GENERALES ─────────────────────────────────────
        (["estoy bien", "todo bien", "ando bien"],                               "estado_general",  "bien"),
        (["estoy mal", "no estoy bien", "ando mal"],                             "estado_general",  "mal"),
    ]

    MEMORY_CHECK_TRIGGERS = [
        "recuerdas", "te acuerdas", "sabes algo de mi", "sabes algo sobre mi",
        "que sabes de mi", "qué sabes de mí", "recuerdas algo", "me conoces",
        "que recuerdas", "qué recuerdas", "acordas", "ya te dije",
        "te dije que", "te conte que", "te conté que",
    ]

    def __init__(self):
        pass

    def _normalize(self, text: str) -> str:
        nfkd = unicodedata.normalize("NFD", text)
        return nfkd.encode("ascii", "ignore").decode("utf-8").lower().strip()

    def is_memory_check(self, message: str) -> bool:
        msg = self._normalize(message)
        return any(trigger in msg for trigger in self.MEMORY_CHECK_TRIGGERS)

    def extract_facts(self, message: str) -> dict:
        msg = self._normalize(message)
        found = {}
        for triggers, key, fixed_value in self.EXTRACTION_RULES:
            for trigger in triggers:
                if trigger in msg:
                    if fixed_value is not None:
                        found[key] = fixed_value
                    else:
                        idx = msg.find(trigger)
                        rest = msg[idx + len(trigger):].strip().split()
                        if rest:
                            found[key] = " ".join(rest[:3])
                    break
        return found

    def build_recall_response(self, semantic_facts: dict, name: str) -> str:
        if not semantic_facts:
            return None
        priority_keys = [
            "comida_favorita", "deporte_interes", "futbol_tiene_equipo",
            "futbol_equipo", "ocupacion", "musica_le_gusta", "estado_general",
        ]
        facts_text = []
        for key in priority_keys:
            val = semantic_facts.get(key)
            if val:
                fact = self._fact_to_human(key, val)
                if fact:
                    facts_text.append(fact)
        for key, val in semantic_facts.items():
            if key not in priority_keys:
                fact = self._fact_to_human(key, val)
                if fact:
                    facts_text.append(fact)
        if not facts_text:
            return None
        if len(facts_text) == 1:
            templates = [
                f"Sí, recuerdo que {facts_text[0]}. ¿Por qué lo preguntas?",
                f"Claro, sé que {facts_text[0]}. ¿Hay algo más que quieras que sepa?",
                f"Mm… sí. Recuerdo que {facts_text[0]}.",
            ]
        else:
            lista = ", ".join(facts_text[:-1]) + f" y {facts_text[-1]}"
            templates = [
                f"Bueno, recuerdo algunas cosas: {lista}. ¿Eso es lo que buscabas?",
                f"Sé que {lista}. No es mucho, pero es lo que tengo jeje.",
                f"Mm… {lista}. ¿Quieres contarme algo más?",
            ]
        return random.choice(templates)

    def _fact_to_human(self, key: str, val: str) -> str:
        mapping = {
            "comida_favorita":     f"te gusta {val}",
            "deporte_interes":     f"te interesa el {val}",
            "futbol_tiene_equipo": ("no tienes equipo de fútbol" if val == "no" else f"tienes equipo de fútbol: {val}"),
            "futbol_equipo":       f"eres del {val}",
            "ocupacion":           f"eres {val}",
            "musica_le_gusta":     "te gusta la música",
            "estado_general":      f"generalmente estás {val}",
        }
        return mapping.get(key, f"{key}: {val}")


class IntentClassifier:
    def __init__(self, semantic_memory: SemanticMemory):
        self.sem = semantic_memory

    def classify(self, message: str) -> str:
        if self.sem.is_memory_check(message):
            return "memory_check"
        return "normal"