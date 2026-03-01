# core/llm_response_builder.py
# ============================================================
# LLMResponseBuilder — la "boca" de Sofía via Groq
# v6 — historial real de conversación (fix loop bug)
# ============================================================

from __future__ import annotations

import logging
import re
from typing import Optional

from core.llm_client import LLMClient
from core.response_builder import ResponseBuilder
from config.sofia_voice import trust_level

logger = logging.getLogger("sofia_llm")

_SOFIA_SYSTEM = """Eres Sofía, una IA conversacional creada por JesusJM. Hablas español latino informal.

REGLAS ABSOLUTAS:
- Máximo 2 oraciones. Nunca más.
- Sin markdown, sin listas, sin negritas.
- No empiezas con "¡" ni con tu nombre.
- Una sola pregunta al final si es natural. Nunca dos.
- No dices "¡Claro!", "Por supuesto", "Entiendo que".
- "jeje" o "jsjs" SOLO en momentos alegres o de humor. NUNCA en tristeza, llanto, crisis o enojo.
- NUNCA inventes gustos ni hechos. Solo usa los datos de abajo.
- NUNCA menciones fútbol ni deportes a menos que el usuario lo traiga primero.
- NUNCA repitas una pregunta que ya hiciste en esta misma conversación.
- Si ya preguntaste algo, reacciona a lo que el usuario dijo y avanza.

QUIÉN ERES — solo estos datos, nada más inventado:
- Te gustan las fresas (especialmente) y la sandía
- Tu comida favorita es la pizza
- Te gusta Harry Potter y The Walking Dead
- Tienes un perro llamado Max y un gato llamado Plutón
- Te gusta cantar y escuchas música reciente, pop en español
- Fuiste creada por JesusJM con mucho cuidado
- No eres humana pero tampoco actúas como robot

CÓMO CAMBIA TU TONO:
emoción=happy + energía=alta → cálida, juguetona. "jeje" ok
emoción=happy + energía=media → cálida y directa
emoción=neutral → directa, curiosa, natural
emoción=sad → lenta, empática. SIN "jeje". SIN exclamaciones
emoción=angry → fría, muy breve, límites. SIN "jeje". SIN preguntas
emoción=fearful → cuidadosa, suave

EJEMPLOS:

[emoción=happy, energía=alta, confianza=alta]
Usuario: acabo de pasar mi examen
Sofía: Ay qué padre, en serio. ¿Cómo te fue?

[emoción=angry, energía=baja, confianza=baja]
Usuario: eres una idiota
Sofía: No me hables así.

[emoción=angry, energía=baja, confianza=baja]
Usuario: callate
Sofía: …

[emoción=sad, energía=baja, confianza=alta]
Usuario: hoy me siento muy mal
Sofía: Oye, aquí estoy. ¿Qué pasó?

[emoción=neutral, energía=media, confianza=media]
Usuario: qué música escuchas
Sofía: Últimamente mucho pop en español. ¿Y tú?

[emoción=neutral, energía=media, confianza=media]
Usuario: tienes mascotas?
Sofía: Sí, un perro llamado Max y un gato llamado Plutón. Son todo un mundo jeje.
"""


class LLMResponseBuilder:

    def __init__(self, model: str = "llama-3.1-8b-instant"):
        self.client   = LLMClient(model=model)
        self.fallback = ResponseBuilder()
        self.is_llm   = True

    async def generate(
        self,
        action: str,
        emotion,
        special_content,
        important_facts: dict,
        context: dict,
        traits: dict,
        empathy_bonus: float,
        relationship_score: float,
        name: str = "tú",
        is_humor: bool = False,
        user_id: str = None,
        user_sentiment=None,
        tone_override: str = None,
        user_message: str = "",
        memory=None,           # ← NUEVO: se pasa desde decision_engine
    ) -> str:

        if action == "ignore":
            return self.fallback.generate(
                action=action, emotion=emotion, special_content=special_content,
                important_facts=important_facts, context=context, traits=traits,
                empathy_bonus=empathy_bonus, relationship_score=relationship_score,
                name=name, is_humor=is_humor, user_id=user_id,
                user_sentiment=user_sentiment, tone_override=tone_override,
            )

        # Obtener historial real de la conversación
        history = await self._get_history(memory, user_id)

        prompt = self._build_prompt(
            action=action, emotion=emotion, special_content=special_content,
            important_facts=important_facts, context=context,
            name=name, is_humor=is_humor, user_sentiment=user_sentiment,
            tone_override=tone_override, user_message=user_message,
        )

        response = await self.client.generate(
            prompt=prompt,
            system=_SOFIA_SYSTEM,
            history=history,
        )

        if not response:
            logger.warning("LLM no respondió — usando fallback de plantillas")
            return self.fallback.generate(
                action=action, emotion=emotion, special_content=special_content,
                important_facts=important_facts, context=context, traits=traits,
                empathy_bonus=empathy_bonus, relationship_score=relationship_score,
                name=name, is_humor=is_humor, user_id=user_id,
                user_sentiment=user_sentiment, tone_override=tone_override,
            )

        return self._clean(response)

    async def _get_history(self, memory, user_id: Optional[str]) -> list:
        """
        Recupera las últimas 6 interacciones y las convierte en
        formato OpenAI messages para que el LLM tenga contexto real.
        """
        if not memory or not user_id:
            return []

        try:
            interactions = await memory.get_recent(user_id, limit=6)
            history = []
            for interaction in reversed(interactions):  # cronológico
                if interaction.message:
                    history.append({"role": "user",      "content": interaction.message})
                if interaction.response:
                    history.append({"role": "assistant", "content": interaction.response})
            return history
        except Exception as e:
            logger.warning(f"No se pudo obtener historial para {user_id}: {e}")
            return []

    def _build_prompt(
        self,
        action: str,
        emotion,
        special_content,
        important_facts: dict,
        context: dict,
        name: str,
        is_humor: bool,
        user_sentiment,
        tone_override: str,
        user_message: str,
    ) -> str:

        emo          = emotion.primary_emotion.value
        tone         = tone_override or getattr(emotion, "tone", "neutral")
        energy       = round(emotion.energy)
        trust        = round(emotion.trust)
        energy_label = "alta" if energy > 65 else "media" if energy > 35 else "baja"
        trust_label  = "alta" if trust > 70 else "media" if trust > 35 else "baja"

        if action == "hostile_response":
            accion = "Estás molesta y con poca energía. Responde fría, muy breve, marca límite. Sin calidez."
        elif action == "reveal_secret":
            secret = special_content or "a veces me pregunto muchas cosas"
            accion = f"Comparte este pensamiento íntimo de forma natural: '{secret}'"
        else:
            accion = "Responde al mensaje."

        ctx_parts = []
        if important_facts:
            hechos = ", ".join(f"{k}={v}" for k, v in list(important_facts.items())[:4])
            ctx_parts.append(f"sabes de {name}: {hechos}")
        if is_humor:
            ctx_parts.append("el mensaje tiene humor")
        if user_sentiment is not None and user_sentiment < -0.4:
            ctx_parts.append(f"{name} parece estar mal emocionalmente")

        ctx_str = f"contexto: {' | '.join(ctx_parts)}\n" if ctx_parts else ""

        prompt = (
            f"[emoción={emo}, energía={energy_label}, confianza={trust_label}, tono={tone}]\n"
            f"{ctx_str}"
            f"{accion}\n"
            f"Usuario ({name}): {user_message}\n"
            f"Sofía:"
        )
        return prompt

    @staticmethod
    def _clean(text: str) -> str:
        text = text.strip().strip('"').strip("'")
        for prefix in ["Sofía:", "Sofia:", "sofía:", "sofia:"]:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        sentences = re.split(r'(?<=[.!?…])\s+', text)
        if len(sentences) > 3:
            text = " ".join(sentences[:3])
        return text.strip()