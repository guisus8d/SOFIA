# storage/database.py
import sqlite3
from models.state import Emotion
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from models.interaction import Interaction
from models.state import EmotionalState
from utils.logger import logger

class Database:
    def __init__(self, db_path: str = "data/bot_data.db"):
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self):
        """Retorna una conexión a la BD"""
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """Crea las tablas si no existen"""
        Path("data").mkdir(exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de interacciones
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    message TEXT,
                    sentiment REAL,
                    response TEXT,
                    timestamp TEXT,
                    emotion_before TEXT,
                    emotion_after TEXT
                )
            """)
            
            # Tabla de estado emocional (solo una fila, la actual)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emotional_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    emotion TEXT,
                    energy REAL,
                    trust REAL,
                    last_updated TEXT
                )
            """)
            
            # Insertar estado inicial si no existe
            cursor.execute("SELECT * FROM emotional_state WHERE id = 1")
            if not cursor.fetchone():
                initial = EmotionalState()
                cursor.execute("""
                    INSERT INTO emotional_state (id, emotion, energy, trust, last_updated)
                    VALUES (1, ?, ?, ?, ?)
                """, (initial.primary_emotion.value, initial.energy, initial.trust, None))
            
            conn.commit()
    
    # --- Interacciones ---
    def save_interaction(self, interaction: Interaction) -> int:
        """Guarda una interacción y retorna su ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interactions 
                (user_id, message, sentiment, response, timestamp, emotion_before, emotion_after)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                interaction.user_id,
                interaction.message,
                interaction.sentiment,
                interaction.response,
                interaction.timestamp.isoformat(),
                interaction.emotion_before,
                interaction.emotion_after
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_user_interactions(self, user_id: str, limit: int = 10) -> List[Interaction]:
        """Recupera las últimas interacciones de un usuario"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, message, sentiment, response, timestamp, emotion_before, emotion_after
                FROM interactions
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
            rows = cursor.fetchall()
            
            interactions = []
            for row in rows:
                interactions.append(Interaction(
                    user_id=row[0],
                    message=row[1],
                    sentiment=row[2],
                    response=row[3],
                    timestamp=datetime.fromisoformat(row[4]),
                    emotion_before=row[5],
                    emotion_after=row[6]
                ))
            return interactions
    
    # --- Estado emocional ---
    def save_emotional_state(self, state: EmotionalState):
        """Guarda el estado emocional actual (siempre id=1)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE emotional_state
                SET emotion = ?, energy = ?, trust = ?, last_updated = ?
                WHERE id = 1
            """, (
                state.primary_emotion.value,
                state.energy,
                state.trust,
                state.last_updated
            ))
            conn.commit()
    
    def load_emotional_state(self) -> EmotionalState:
        """Carga el último estado emocional guardado"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT emotion, energy, trust, last_updated FROM emotional_state WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return EmotionalState(
                    primary_emotion=Emotion(row[0]),
                    energy=row[1],
                    trust=row[2],
                    last_updated=row[3]
                )
            else:
                return EmotionalState()  # fallback
    
    # Opcional: estadísticas
    def get_average_sentiment_for_user(self, user_id: str) -> float:
        """Calcula el sentimiento promedio de las interacciones de un usuario"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT AVG(sentiment) FROM interactions
                WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()[0]
            return result if result is not None else 0.0