# storage/database.py
# ============================================================
# SocialBot v0.11.0
# CAMBIOS vs v0.10.0:
#   - Migración completa SQLite → PostgreSQL
#   - Usa DATABASE_URL (Railway la inyecta automáticamente)
#   - Misma interfaz pública: nada más en el proyecto cambia
#   - Placeholders ? → %s  |  AUTOINCREMENT → SERIAL
#   - INSERT OR REPLACE → INSERT ... ON CONFLICT ... DO UPDATE
# ============================================================

import json
import os
from datetime import datetime
from typing import List, Optional

import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor

from models.state import EmotionalState
from models.interaction import Interaction
from models.user_profile import UserProfile
from utils.logger import logger


class Database:
    def __init__(self, db_path: str = None):
        # db_path se ignora — Railway provee DATABASE_URL
        self.database_url = os.environ["DATABASE_URL"]
        self._init_db()

    def _get_connection(self):
        return psycopg2.connect(self.database_url)

    # --------------------------------------------------
    # INIT
    # --------------------------------------------------

    def _init_db(self):
        with self._get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS interactions (
                        id            SERIAL PRIMARY KEY,
                        user_id       TEXT NOT NULL,
                        message       TEXT,
                        sentiment     REAL,
                        response      TEXT,
                        timestamp     TEXT,
                        emotion_before TEXT,
                        emotion_after  TEXT
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id              TEXT PRIMARY KEY,
                        emotional_state      TEXT,
                        interaction_count    INTEGER DEFAULT 0,
                        communication_style  TEXT DEFAULT 'neutral',
                        first_seen           TEXT,
                        last_seen            TEXT,
                        topics               TEXT,
                        personality_traits   TEXT,
                        important_facts      TEXT,
                        relationship_damage  REAL DEFAULT 0.0,
                        important_quotes     TEXT,
                        semantic_facts       TEXT
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        user_id           TEXT PRIMARY KEY,
                        date              TEXT NOT NULL,
                        session_count     INTEGER DEFAULT 1,
                        topics            TEXT,
                        important_facts   TEXT,
                        last_session_tone TEXT DEFAULT 'neutral'
                    )
                """)

                conn.commit()

                # Migraciones seguras para bases de datos existentes
                _safe_migrations = [
                    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS relationship_damage REAL DEFAULT 0.0",
                    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS important_quotes TEXT",
                    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS semantic_facts TEXT",
                    "ALTER TABLE sessions     ADD COLUMN IF NOT EXISTS last_session_tone TEXT DEFAULT 'neutral'",
                ]
                for migration in _safe_migrations:
                    try:
                        cur.execute(migration)
                        conn.commit()
                    except Exception as e:
                        conn.rollback()
                        logger.warning(f"Migración omitida: {e}")

    # --------------------------------------------------
    # INTERACTIONS
    # --------------------------------------------------

    def save_interaction(self, interaction: Interaction) -> int:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO interactions
                        (user_id, message, sentiment, response, timestamp,
                         emotion_before, emotion_after)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    interaction.user_id,
                    interaction.message,
                    interaction.sentiment,
                    interaction.response,
                    interaction.timestamp.isoformat(),
                    interaction.emotion_before,
                    interaction.emotion_after,
                ))
                conn.commit()
                return cur.fetchone()[0]

    def get_user_interactions(self, user_id: str, limit: int = 10) -> List[Interaction]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, message, sentiment, response, timestamp,
                           emotion_before, emotion_after
                    FROM interactions
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (user_id, limit))

                return [
                    Interaction(
                        user_id=row[0], message=row[1], sentiment=row[2],
                        response=row[3],
                        timestamp=datetime.fromisoformat(row[4]),
                        emotion_before=row[5], emotion_after=row[6],
                    )
                    for row in cur.fetchall()
                ]

    # --------------------------------------------------
    # USER PROFILES
    # --------------------------------------------------

    def save_user_profile(self, profile: UserProfile):
        emotional_state_json = (
            json.dumps(profile.emotional_state.to_dict())
            if profile.emotional_state else None
        )
        topics_str    = ",".join(profile.topics)           if profile.topics               else None
        traits_json   = json.dumps(profile.personality_offsets) if profile.personality_offsets else None
        facts_json    = json.dumps(profile.important_facts)     if profile.important_facts      else None
        quotes_json   = json.dumps(profile.important_quotes)    if profile.important_quotes     else None
        semantic_json = json.dumps(profile.semantic_facts)      if profile.semantic_facts       else None

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_profiles
                        (user_id, emotional_state, interaction_count,
                         communication_style, first_seen, last_seen,
                         topics, personality_traits, important_facts,
                         relationship_damage, important_quotes, semantic_facts)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        emotional_state     = EXCLUDED.emotional_state,
                        interaction_count   = EXCLUDED.interaction_count,
                        communication_style = EXCLUDED.communication_style,
                        first_seen          = EXCLUDED.first_seen,
                        last_seen           = EXCLUDED.last_seen,
                        topics              = EXCLUDED.topics,
                        personality_traits  = EXCLUDED.personality_traits,
                        important_facts     = EXCLUDED.important_facts,
                        relationship_damage = EXCLUDED.relationship_damage,
                        important_quotes    = EXCLUDED.important_quotes,
                        semantic_facts      = EXCLUDED.semantic_facts
                """, (
                    profile.user_id,
                    emotional_state_json,
                    profile.interaction_count,
                    profile.communication_style,
                    profile.first_seen.isoformat() if profile.first_seen else None,
                    profile.last_seen.isoformat()  if profile.last_seen  else None,
                    topics_str,
                    traits_json,
                    facts_json,
                    profile.relationship_damage,
                    quotes_json,
                    semantic_json,
                ))
                conn.commit()

    def load_user_profile(self, user_id: str) -> Optional[UserProfile]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, emotional_state, interaction_count,
                           communication_style, first_seen, last_seen,
                           topics, personality_traits, important_facts,
                           relationship_damage, important_quotes, semantic_facts
                    FROM user_profiles
                    WHERE user_id = %s
                """, (user_id,))

                row = cur.fetchone()
                if not row:
                    return None

        topics  = [t.strip() for t in row[6].split(",") if t.strip()] if row[6] else []
        data = {
            "user_id":             row[0],
            "emotional_state":     json.loads(row[1])  if row[1]  else None,
            "interaction_count":   row[2],
            "communication_style": row[3],
            "first_seen":          row[4],
            "last_seen":           row[5],
            "topics":              topics,
            "personality_traits":  json.loads(row[7])  if row[7]  else {},
            "important_facts":     json.loads(row[8])  if row[8]  else {},
            "relationship_damage": row[9]              if row[9] is not None else 0.0,
            "important_quotes":    json.loads(row[10]) if row[10] else [],
            "semantic_facts":      json.loads(row[11]) if row[11] else {},
        }
        return UserProfile.from_dict(data)

    # --------------------------------------------------
    # STATS
    # --------------------------------------------------

    def get_average_sentiment_for_user(self, user_id: str) -> float:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT AVG(sentiment) FROM interactions WHERE user_id = %s
                """, (user_id,))
                result = cur.fetchone()[0]
                return float(result) if result is not None else 0.0

    # --------------------------------------------------
    # SESSIONS
    # --------------------------------------------------

    def save_session(
        self,
        user_id: str,
        topics: List[str],
        important_facts: dict,
        session_count: int,
        last_session_tone: str = "neutral",
    ):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sessions
                        (user_id, date, session_count, topics,
                         important_facts, last_session_tone)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        date              = EXCLUDED.date,
                        session_count     = EXCLUDED.session_count,
                        topics            = EXCLUDED.topics,
                        important_facts   = EXCLUDED.important_facts,
                        last_session_tone = EXCLUDED.last_session_tone
                """, (
                    user_id,
                    datetime.now().isoformat(),
                    session_count,
                    ",".join(topics[:10]) if topics else "",
                    json.dumps(important_facts) if important_facts else "{}",
                    last_session_tone,
                ))
                conn.commit()

    def load_last_session(self, user_id: str) -> Optional[dict]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT date, session_count, topics, important_facts, last_session_tone
                    FROM sessions
                    WHERE user_id = %s
                """, (user_id,))

                row = cur.fetchone()
                if not row:
                    return None

        topics = [t.strip() for t in row[2].split(",") if t.strip()] if row[2] else []
        return {
            "date":              datetime.fromisoformat(row[0]),
            "session_count":     row[1],
            "topics":            topics,
            "important_facts":   json.loads(row[3]) if row[3] else {},
            "last_session_tone": row[4] if row[4] else "neutral",
        }