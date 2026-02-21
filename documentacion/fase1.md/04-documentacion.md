🛠️ Paso 2: Utilidades
utils/text_analyzer.py

Análisis de sentimiento básico sin ML externo.
python

# utils/text_analyzer.py
import re
from typing import List

class TextAnalyzer:
    """Analizador de texto simple basado en palabras clave"""
    
    def __init__(self):
        # Palabras positivas y negativas en español (puedes ampliarlas)
        self.positive_words = {
            "gracias", "genial", "buen", "bien", "excelente", "perfecto",
            "amor", "❤️", "😊", "👍", "feliz", "alegre", "maravilloso",
            "te quiero", "te amo", "helpful", "thanks", "good", "great"
        }
        self.negative_words = {
            "mal", "peor", "odio", "estúpido", "tonto", "feo",
            "👎", "😠", "😡", "horrible", "terrible", "asco",
            "imbécil", "idiota", "hate", "bad", "stupid"
        }
        # Intensificadores
        self.intensifiers = {"muy", "mucho", "bastante", "demasiado", "super", "really", "very"}

    def analyze_sentiment(self, text: str) -> float:
        """
        Retorna un valor entre -1 (muy negativo) y 1 (muy positivo)
        """
        text_lower = text.lower()
        
        # Detectar negaciones (no, nunca, etc.) - simple
        negation_words = {"no", "nunca", "jamás", "not", "never"}
        words = text_lower.split()
        
        score = 0.0
        found_words = 0
        negate = False
        
        for i, word in enumerate(words):
            # Limpiar palabra de signos de puntuación
            word = re.sub(r'[^\w]', '', word)
            if not word:
                continue
            
            # Verificar si es negación
            if word in negation_words:
                negate = True
                continue
            
            # Buscar en listas de palabras
            multiplier = 1.0
            if i > 0 and words[i-1] in self.intensifiers:
                multiplier = 1.5  # intensificador
            
            if word in self.positive_words:
                score += (1.0 * multiplier) * (-1 if negate else 1)
                found_words += 1
                negate = False  # Reiniciar negación después de una palabra
            elif word in self.negative_words:
                score += (-1.0 * multiplier) * (-1 if negate else 1)
                found_words += 1
                negate = False
            else:
                # Mantener negación si no se aplicó a una palabra
                pass
        
        if found_words == 0:
            return 0.0
        
        # Normalizar a rango -1..1
        normalized = score / found_words
        return max(-1.0, min(1.0, normalized))

    def extract_keywords(self, text: str, max_words: int = 5) -> List[str]:
        """Extrae palabras clave (simplemente palabras largas no comunes)"""
        words = re.findall(r'\b\w+\b', text.lower())
        # Filtrar palabras comunes y cortas
        stopwords = {"de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por", "un", "para", "con", "no", "una", "su", "al", "lo", "como", "más", "pero", "sus", "le", "ya", "o", "fue", "este", "sí", "mi"}
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        # Devolver las primeras max_words
        return keywords[:max_words]

utils/logger.py

Logger simple para depuración.
python

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

