# core/tool_engine.py
# ============================================================
# SocialBot v0.10.2
# CAMBIOS vs v0.10.1:
#   - FIX CRÍTICO: indentación correcta en _wiki_search — data y extract
#     ahora se leen DENTRO del async with session, no fuera.
#   - NUEVO: _wiki_find_title usa la API de búsqueda de Wikipedia para
#     encontrar el título exacto cuando el slug directo falla.
#     Ejemplo: "nikola tesla" → "Nikola Tesla" → summary correcto.
#   - MANTIENE: normalización de tildes, triggers, blockers de v0.10.1
# ============================================================

import aiohttp
import unicodedata
import random
from typing import Optional
from utils.logger import logger


def _norm(text: str) -> str:
    """Quita tildes y convierte a minúsculas."""
    nfkd = unicodedata.normalize("NFD", text)
    return nfkd.encode("ascii", "ignore").decode("utf-8").lower()


# ── Triggers — todos sin tildes, se comparan contra texto normalizado ──

SEARCH_TRIGGERS = [
    # quién / qué es / fue
    "quien es ", "quien fue ", "quienes son ",
    "que es ", "que fue ", "que son ",
    # cuándo
    "cuando fue ", "cuando nacio", "cuando murio", "cuando empezo",
    "cuando termino", "cuando se fundo", "cuando ocurrio",
    # cómo
    "como funciona", "como se hace", "como se llama", "como se dice",
    "como se calcula", "como se define",
    # dónde
    "donde esta ", "donde queda ", "donde nacio ", "donde murio ",
    "donde se encuentra",
    # cuánto / cuál
    "cuanto cuesta", "cuantos ", "cuantas ", "cual es la capital",
    "cual es el ", "cuales son ",
    # qué significa / para qué
    "que significa ", "para que sirve", "para que se usa",
    # de dónde / qué pasó
    "de donde viene", "de donde es ",
    "que paso con", "que paso en", "que paso el ",
    # búsquedas directas / implícitas
    "busca ", "buscame ", "dime algo sobre ", "cuentame sobre ",
    "investiga ", "que sabes de ", "sabes algo de ",
    "informacion sobre", "habla de ", "explicame ",
    "quien invento ", "quien descubrio ", "quien creo ",
    "cuando fue creado", "cuando fue fundado",
]

# Bloqueadores emocionales — sin tildes
SEARCH_BLOCKERS = [
    "me siento", "estoy triste", "estoy mal", "te quiero",
    "me gusta", "te odio", "estoy feliz", "me duele",
    "me da miedo", "tengo miedo", "estoy solo", "me arrepiento",
    "a veces pienso", "nadie sabe", "quisiera", "ojala",
    "me pregunto si", "no se que hacer", "necesito ayuda con",
]


class ToolEngine:
    """Motor de herramientas externas para Sofía. v0.10.2"""

    DDGO_URL = "https://api.duckduckgo.com/"

    def __init__(self):
        pass

    # ──────────────────────────────────────────────────────────────
    # INTERFAZ PÚBLICA
    # ──────────────────────────────────────────────────────────────

    # Prefijos de búsqueda explícita — bypasan el cooldown en decision_engine.
    # Incluye preguntas de conocimiento directo: el usuario espera un dato concreto,
    # no importa cuándo fue la última búsqueda.
    EXPLICIT_PREFIXES = {
        "busca ", "buscame ", "investiga ", "explicame ",
        "que es ", "quien es ", "que fue ", "quien fue ",
        "que son ", "quienes son ", "como funciona ", "para que sirve ",
        "donde esta ", "donde queda ", "cual es la capital",
    }

    def should_search(self, message: str) -> bool:
        # FIX v0.10.3: strip ¿? antes de normalizar — "¿qué es la fotosíntesis?"
        # fallaba porque "¿que es" no matcheaba el trigger "que es ".
        msg = _norm(message.replace("¿", "").replace("?", ""))
        if any(b in msg for b in SEARCH_BLOCKERS):
            return False
        return any(t in msg for t in SEARCH_TRIGGERS)

    def is_explicit_search(self, message: str) -> bool:
        """Retorna True si el mensaje es un comando explícito de búsqueda.
        Estos bypasan el cooldown — el usuario está pidiendo buscar directamente."""
        msg = _norm(message.replace("¿", "").replace("?", ""))
        return any(msg.startswith(p) for p in self.EXPLICIT_PREFIXES)

    async def search(self, message: str) -> Optional[str]:
        query = self._extract_query(message)
        if not query:
            return None
        try:
            return await self._search(query)
        except Exception as e:
            logger.warning(f"[ToolEngine] Error en búsqueda '{query}': {e}")
            return None

    def wrap_result(self, raw_result: str, message: str,
                    energy: float, trust: float, emotion: str = "neutral") -> str:
        if not raw_result or len(raw_result.strip()) < 10:
            return self._no_result_response(trust)

        snippet = self._clean_snippet(raw_result.strip())
        if not snippet or len(snippet) < 10:
            return self._no_result_response(trust)

        if len(snippet) > 280:
            cut = snippet[:280]
            last_period = max(cut.rfind("."), cut.rfind(","))
            snippet = cut[:last_period + 1] if last_period > 150 else cut + "…"

        intro  = self._pick_intro(energy, trust, emotion)
        outro  = self._pick_outro(trust)
        suffix = f" {outro}" if outro else ""
        return f"{intro} {snippet}{suffix}"

    def _clean_snippet(self, text: str) -> str:
        """Limpia el snippet: quita pronunciaciones IPA, paréntesis vacíos, espacios extra."""
        import re
        text = re.sub(r'/[^/]{1,80}/', '', text)
        text = re.sub(r'\(\s*[;,]?\s*\)', '', text)
        text = re.sub(r'\(\s+\)', '', text)
        text = re.sub(r'  +', ' ', text).strip()
        text = text.lstrip(' ,;()'  )
        return text.strip()

    # ──────────────────────────────────────────────────────────────
    # PIPELINE DE BÚSQUEDA: Wikipedia ES → Wikipedia EN → DuckDuckGo
    # ──────────────────────────────────────────────────────────────

    async def _search(self, query: str) -> Optional[str]:
        for lang in ("es", "en"):
            result = await self._wiki_summary_direct(lang, query)
            if result:
                return result
            title = await self._wiki_find_title(lang, query)
            if title:
                result = await self._wiki_summary_direct(lang, title)
                if result:
                    return result
        return await self._ddgo_instant(query)

    async def _wiki_summary_direct(self, lang: str, query: str) -> Optional[str]:
        """GET /page/summary/{slug} — lectura dentro del context manager."""
        # Capitalizar cada palabra para mejorar match en Wikipedia ES
        slug = query.strip().title().replace(" ", "_")
        url  = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{slug}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=5),
                    headers={"User-Agent": "SofiaBot/0.10.2"},
                    allow_redirects=True,
                ) as resp:
                    if resp.status != 200:
                        return None
                    data    = await resp.json(content_type=None)
                    extract = data.get("extract", "").strip()
                    if not extract or len(extract) < 30:
                        return None
                    first = extract.split(". ")[0]
                    return (first + ".") if len(first) > 30 else extract
        except Exception as e:
            logger.debug(f"[ToolEngine] wiki_summary {lang}/{slug}: {e}")
            return None

    async def _wiki_find_title(self, lang: str, query: str) -> Optional[str]:
        """Busca el título exacto usando la API de búsqueda de Wikipedia."""
        url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query", "list": "search",
            "srsearch": query, "srlimit": "1", "format": "json",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params,
                    timeout=aiohttp.ClientTimeout(total=5),
                    headers={"User-Agent": "SofiaBot/0.10.2"},
                ) as resp:
                    if resp.status != 200:
                        return None
                    data    = await resp.json(content_type=None)
                    results = data.get("query", {}).get("search", [])
                    return results[0].get("title") if results else None
        except Exception as e:
            logger.debug(f"[ToolEngine] wiki_find_title {lang}/{query}: {e}")
            return None

    async def _ddgo_instant(self, query: str) -> Optional[str]:
        """DuckDuckGo Instant Answer — fallback final."""
        params = {
            "q": query, "format": "json",
            "no_html": "1", "skip_disambig": "1",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.DDGO_URL, params=params,
                    timeout=aiohttp.ClientTimeout(total=5),
                    headers={"User-Agent": "SofiaBot/0.10.2"},
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json(content_type=None)
            for field in ("AbstractText", "Answer", "Definition"):
                value = data.get(field, "").strip()
                if value and len(value) > 20:
                    return value
            for topic in data.get("RelatedTopics", []):
                text = topic.get("Text", "").strip()
                if text and len(text) > 20:
                    return text
        except Exception as e:
            logger.debug(f"[ToolEngine] ddgo: {e}")
        return None

    # ──────────────────────────────────────────────────────────────
    # LIMPIEZA DE QUERY
    # ──────────────────────────────────────────────────────────────

    def _extract_query(self, message: str) -> str:
        msg      = message.strip()
        msg_norm = _norm(msg)

        prefixes = [
            "busca ", "buscame ", "dime algo sobre ", "cuentame sobre ",
            "investiga ", "que sabes de ", "sabes algo de ",
            "informacion sobre ", "habla de ", "explicame ",
            "que es ", "quien es ", "quienes son ",
            "que fue ", "quien fue ",
            "cuando fue ", "cuando nacio ", "cuando murio ",
            "que paso con ", "que paso en ",
            "que significa ",
            "como funciona ", "como se hace ", "como se llama ",
            "para que sirve ", "para que se usa ",
            "de donde viene ", "de donde es ",
            "donde esta ", "donde queda ", "donde nacio ",
            "cual es la capital de ", "cual es el ", "cuales son ",
            "quien invento ", "quien descubrio ", "quien creo ",
        ]

        for prefix in prefixes:
            if msg_norm.startswith(prefix):
                msg = msg[len(prefix):].strip()
                break

        msg = msg.replace("¿", "").replace("?", "").strip()
        return msg if len(msg) > 2 else ""

    # ──────────────────────────────────────────────────────────────
    # VOZ DE SOFÍA
    # ──────────────────────────────────────────────────────────────

    def _pick_intro(self, energy: float, trust: float, emotion: str) -> str:
        if energy < 30:
            return random.choice([
                "Mm… busqué un poco.",
                "Encontré algo.",
                "Estoy cansada pero aquí va:",
                "Mm… dice que",
            ])
        if trust > 70:
            return random.choice([
                "¡Oye! Fui a buscar y encontré esto:",
                "Mm… busqué porque me dio curiosidad también.",
                "Mira lo que encontré jeje —",
                "Oye, fui a revisar y:",
                "Encontré algo interesante:",
            ])
        return random.choice([
            "Busqué un momento:",
            "Mm… encontré esto:",
            "Aquí hay algo:",
            "Fui a buscar:",
            "Mm… según lo que encontré,",
            "Oye, busqué un poco y:",
        ])

    def _pick_outro(self, trust: float) -> Optional[str]:
        if random.random() > 0.55:
            return None
        if trust > 70:
            return random.choice([
                "¿Eso era lo que querías saber?",
                "¿Te sirve eso?",
                "¿Qué más te da curiosidad?",
                "Ahora me das curiosidad a mí también jeje. ¿Qué más sabes?",
            ])
        return random.choice([
            "¿Eso era lo que buscabas?",
            "¿Te sirvió?",
            "¿Hay algo más que quieras saber?",
        ])

    def _no_result_response(self, trust: float) -> str:
        if trust > 70:
            return random.choice([
                "Fui a buscar y no encontré nada claro. ¿Puedes darme más contexto?",
                "Mm… busqué pero no encontré nada útil. ¿Cómo lo formularías diferente?",
                "Nada concreto en lo que encontré. ¿Me das más detalles?",
            ])
        return random.choice([
            "Busqué pero no encontré nada útil. ¿Puedes ser más específico?",
            "Mm… no encontré respuesta clara sobre eso.",
            "No tengo información sobre eso ahora mismo.",
        ])