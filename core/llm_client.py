# core/llm_client.py
# ============================================================
# LLMClient — cliente async para Groq API
# v2 — soporte para historial de conversación
# ============================================================

from __future__ import annotations

import logging
import asyncio
import os
from typing import Optional, List

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("sofia_llm")

GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.1-8b-instant"


class LLMClient:

    def __init__(self, model: str = DEFAULT_MODEL, timeout: int = 30):
        self.model   = model
        self.timeout = timeout
        self.api_key = os.getenv("GROQ_API_KEY", "")

    async def generate(
        self,
        prompt: str,
        system: str = "",
        history: Optional[List[dict]] = None,
    ) -> Optional[str]:
        """
        history: lista de dicts con formato OpenAI:
          [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
        """
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None, self._call_sync, prompt, system, history or []
            )
            return result
        except Exception as e:
            logger.warning(f"LLMClient error: {e}")
            return None

    def _call_sync(self, prompt: str, system: str, history: List[dict]) -> Optional[str]:
        if not self.api_key:
            logger.error("GROQ_API_KEY no configurada en .env")
            return None

        messages = []
        if system:
            messages.append({"role": "system", "content": system})

        # Insertar historial entre system y el mensaje actual
        messages.extend(history)

        # Mensaje actual del usuario
        messages.append({"role": "user", "content": prompt})

        try:
            r = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model":       self.model,
                    "messages":    messages,
                    "max_tokens":  120,
                    "temperature": 0.85,
                    "top_p":       0.9,
                },
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return None