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