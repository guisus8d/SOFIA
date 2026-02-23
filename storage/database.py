# storage/database.py
# ============================================================
# SocialBot v0.5.0 — Memoria Episódica
# Cambios:
#   - Nueva tabla `sessions` para recordar la última sesión
#   - Métodos: save_session, load_last_session
#   - Todo lo demás igual, sin romper nada existente
# ============================================================

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from models.state import Emotion, EmotionalState
from models.interaction import Interaction
from models.user_profile import UserProfile
from utils.logger import logger


class Database:
    def __init__(self, db_path: str = "data/bot_data.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    # --------------------------------------------------
    # INIT DATABASE
    # --------------------------------------------------

    def _init_db(self):
        Path("data").mkdir(exist_ok=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Interactions
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

            # Emotional State Global
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emotional_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    emotion TEXT,
                    energy REAL,
                    trust REAL,
                    last_updated TEXT
                )
            """)

            # User Profiles
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    emotional_state TEXT,
                    interaction_count INTEGER DEFAULT 0,
                    communication_style TEXT DEFAULT 'neutral',
                    first_seen TEXT,
                    last_seen TEXT,
                    topics TEXT,
                    personality_traits TEXT,
                    important_facts TEXT,
                    relationship_damage REAL DEFAULT 0.0
                )
            """)

            # -------------------------
            # 🆕 v0.5.0 — Sessions
            # Guarda un resumen de la última sesión por usuario.
            # Solo se mantiene 1 registro por user_id (INSERT OR REPLACE).
            # -------------------------
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    session_count INTEGER DEFAULT 1,
                    topics TEXT,
                    important_facts TEXT
                )
            """)

            conn.commit()

            # Migraciones para DBs existentes
            for migration in [
                "ALTER TABLE user_profiles ADD COLUMN relationship_damage REAL DEFAULT 0.0",
            ]:
                try:
                    cursor.execute(migration)
                    conn.commit()
                except sqlite3.OperationalError:
                    pass

            # Estado emocional inicial
            cursor.execute("SELECT * FROM emotional_state WHERE id = 1")
            if not cursor.fetchone():
                initial = EmotionalState()
                cursor.execute("""
                    INSERT INTO emotional_state (id, emotion, energy, trust, last_updated)
                    VALUES (1, ?, ?, ?, ?)
                """, (initial.primary_emotion.value, initial.energy, initial.trust, None))
                conn.commit()

    # --------------------------------------------------
    # INTERACTIONS
    # --------------------------------------------------

    def save_interaction(self, interaction: Interaction) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interactions
                (user_id, message, sentiment, response, timestamp,
                 emotion_before, emotion_after)
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, message, sentiment, response, timestamp,
                       emotion_before, emotion_after
                FROM interactions
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))

            rows = cursor.fetchall()
            return [
                Interaction(
                    user_id=row[0], message=row[1], sentiment=row[2],
                    response=row[3],
                    timestamp=datetime.fromisoformat(row[4]),
                    emotion_before=row[5], emotion_after=row[6]
                )
                for row in rows
            ]

    # --------------------------------------------------
    # USER PROFILES
    # --------------------------------------------------

    def save_user_profile(self, profile: UserProfile):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            emotional_state_json = (
                json.dumps(profile.emotional_state.to_dict())
                if profile.emotional_state else None
            )
            topics_str   = ",".join(profile.topics) if profile.topics else None
            traits_json  = json.dumps(profile.personality_offsets) if profile.personality_offsets else None
            facts_json   = json.dumps(profile.important_facts) if profile.important_facts else None

            cursor.execute("""
                INSERT OR REPLACE INTO user_profiles
                (user_id, emotional_state, interaction_count,
                 communication_style, first_seen, last_seen,
                 topics, personality_traits, important_facts, relationship_damage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.user_id,
                emotional_state_json,
                profile.interaction_count,
                profile.communication_style,
                profile.first_seen.isoformat() if profile.first_seen else None,
                profile.last_seen.isoformat() if profile.last_seen else None,
                topics_str,
                traits_json,
                facts_json,
                profile.relationship_damage
            ))
            conn.commit()

    def load_user_profile(self, user_id: str) -> Optional[UserProfile]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, emotional_state, interaction_count,
                       communication_style, first_seen, last_seen,
                       topics, personality_traits, important_facts, relationship_damage
                FROM user_profiles WHERE user_id = ?
            """, (user_id,))

            row = cursor.fetchone()
            if not row:
                return None

            emotional_state_data = json.loads(row[1]) if row[1] else None
            topics               = row[6].split(",") if row[6] else []
            traits_data          = json.loads(row[7]) if row[7] else {}
            facts_data           = json.loads(row[8]) if row[8] else {}
            relationship_damage  = row[9] if row[9] is not None else 0.0

            data = {
                "user_id": row[0],
                "emotional_state": emotional_state_data,
                "interaction_count": row[2],
                "communication_style": row[3],
                "first_seen": row[4],
                "last_seen": row[5],
                "topics": topics,
                "personality_traits": traits_data,
                "important_facts": facts_data,
                "relationship_damage": relationship_damage
            }
            return UserProfile.from_dict(data)

    # --------------------------------------------------
    # STATS
    # --------------------------------------------------

    def get_average_sentiment_for_user(self, user_id: str) -> float:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT AVG(sentiment) FROM interactions WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()[0]
            return result if result is not None else 0.0

    # --------------------------------------------------
    # 🆕 v0.5.0 — SESSIONS
    # --------------------------------------------------

    def save_session(
        self,
        user_id: str,
        topics: List[str],
        important_facts: dict,
        session_count: int
    ):
        """
        Guarda (o actualiza) el resumen de la sesión actual.
        Solo existe 1 registro por usuario — siempre es la última sesión.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sessions
                (user_id, date, session_count, topics, important_facts)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                datetime.now().isoformat(),
                session_count,
                ",".join(topics[:10]) if topics else "",
                json.dumps(important_facts) if important_facts else "{}"
            ))
            conn.commit()

    def load_last_session(self, user_id: str) -> Optional[dict]:
        """
        Carga el resumen de la última sesión del usuario.
        Devuelve None si no existe (usuario nuevo).
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, session_count, topics, important_facts
                FROM sessions WHERE user_id = ?
            """, (user_id,))

            row = cursor.fetchone()
            if not row:
                return None

            topics = [t.strip() for t in row[2].split(",") if t.strip()] if row[2] else []
            facts  = json.loads(row[3]) if row[3] else {}

            return {
                "date":          datetime.fromisoformat(row[0]),
                "session_count": row[1],
                "topics":        topics,
                "important_facts": facts
            }