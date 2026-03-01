# config/voice/_base.py
# ============================================================
# Utilidades base compartidas por todos los módulos de voz.
# Sin dependencias internas — solo stdlib.
# ============================================================

import unicodedata as _uc
import random
from typing import Optional


def _normalize(text: str) -> str:
    """Quita tildes y convierte a minúsculas."""
    nfkd = _uc.normalize("NFD", text)
    return nfkd.encode("ascii", "ignore").decode("utf-8").lower()


def pick(lista: list) -> str:
    """Elige un elemento aleatorio de una lista. Retorna '' si está vacía."""
    return random.choice(lista) if lista else ""


def trust_level(trust: float) -> str:
    """Convierte un valor numérico de trust a una categoría string."""
    if trust > 70:
        return "trust_high"
    elif trust > 35:
        return "trust_mid"
    else:
        return "trust_low"