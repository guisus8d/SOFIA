# storage/database.py
# ============================================================
# SocialBot v0.11.0
# CAMBIOS vs v0.10.0:
#   - Soporte dual: PostgreSQL (Railway) o SQLite (local/fallback)
#   - Si DATABASE_URL está presente → Postgres
#   - Si no → SQLite en data/bot_data.db  (desarrollo local)
#   - Misma interfaz pública: nada más en el proyecto cambia
# ============================================================

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from models.interaction import Interaction
from models.user_profile import UserProfile
from utils.logger import logger

_DATABASE_URL = os.environ.get("DATABASE_URL")

if _DATABASE_URL:
    import psycopg2
    logger.info("🐘 Usando PostgreSQL")
else:
    logger.warning("⚠️  DATABASE_URL no encontrada — usando SQLite (solo desarrollo)")


# ============================================================
# Helpers de compatibilidad Postgres ↔ SQLite
# ============================================================

def _ph(n: int = 1) -> str:
    """n placeholders según el driver activo."""
    ph = "%s" if _DATABASE_URL else "?"
    return ", ".join([ph] * n)


def _get_raw_connection():
    if _DATABASE_URL:
        return psycopg2.connect(_DATABASE_URL)
    Path("data").mkdir(exist_ok=True)
    return sqlite3.connect("data/bot_data.db")


@contextmanager
def _cursor():
    conn = _get_raw_connection()
    try:
        if _DATABASE_URL:
            with conn, conn.cursor() as cur:
                yield cur, conn
        else:
            cur = conn.cursor()
            try:
                yield cur, conn
            finally:
                cur.close()
        conn.commit()
    finally:
        conn.close()


# ============================================================
# Database
# ============================================================

class Database:
    def __init__(self, db_path: str = "data/bot_data.db"):
        # db_path solo aplica en modo SQLite, se ignora en Postgres
        self._init_db()

    # ----------------------------------------------------------
    # INIT / MIGRACIONES
    # ----------------------------------------------------------

    def _init_db(self):
        pk = "SERIAL PRIMARY KEY" if _DATABASE_URL else "INTEGER PRIMARY KEY AUTOINCREMENT"

        with _cursor() as (cur, conn):
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS interactions (
                    id             {pk},
                    user_id        TEXT NOT NULL,
                    message        TEXT,
                    sentiment      REAL,
                    response       TEXT,
                    timestamp      TEXT,
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

        # Migraciones retrocompatibles
        if_not = "IF NOT EXISTS" if _DATABASE_URL else ""
        migrations = [
            f"ALTER TABLE user_profiles ADD COLUMN {if_not} relationship_damage REAL DEFAULT 0.0",
            f"ALTER TABLE user_profiles ADD COLUMN {if_not} important_quotes TEXT",
            f"ALTER TABLE user_profiles ADD COLUMN {if_not} semantic_facts TEXT",
            f"ALTER TABLE sessions      ADD COLUMN {if_not} last_session_tone TEXT DEFAULT 'neutral'",
        ]
        for sql in migrations:
            try:
                with _cursor() as (cur, conn):
                    cur.execute(sql)
                    conn.commit()
            except Exception:
                pass  # columna ya existe

    # ----------------------------------------------------------
    # INTERACTIONS
    # ----------------------------------------------------------

    def save_interaction(self, interaction: Interaction) -> int:
        returning = "RETURNING id" if _DATABASE_URL else ""
        sql = f"""
            INSERT INTO interactions
                (user_id, message, sentiment, response, timestamp,
                 emotion_before, emotion_after)
            VALUES ({_ph(7)}) {returning}
        """
        params = (
            interaction.user_id, interaction.message, interaction.sentiment,
            interaction.response, interaction.timestamp.isoformat(),
            interaction.emotion_before, interaction.emotion_after,
        )
        with _cursor() as (cur, conn):
            cur.execute(sql, params)
            conn.commit()
            if _DATABASE_URL:
                return cur.fetchone()[0]
            return cur.lastrowid

    def get_user_interactions(self, user_id: str, limit: int = 10) -> List[Interaction]:
        sql = f"""
            SELECT user_id, message, sentiment, response, timestamp,
                   emotion_before, emotion_after
            FROM interactions
            WHERE user_id = {_ph(1)}
            ORDER BY timestamp DESC
            LIMIT {_ph(1)}
        """
        with _cursor() as (cur, _):
            cur.execute(sql, (user_id, limit))
            return [
                Interaction(
                    user_id=r[0], message=r[1], sentiment=r[2], response=r[3],
                    timestamp=datetime.fromisoformat(r[4]),
                    emotion_before=r[5], emotion_after=r[6],
                )
                for r in cur.fetchall()
            ]

    # ----------------------------------------------------------
    # USER PROFILES
    # ----------------------------------------------------------

    def save_user_profile(self, profile: UserProfile):
        params = (
            profile.user_id,
            json.dumps(profile.emotional_state.to_dict()) if profile.emotional_state else None,
            profile.interaction_count,
            profile.communication_style,
            profile.first_seen.isoformat() if profile.first_seen else None,
            profile.last_seen.isoformat()  if profile.last_seen  else None,
            ",".join(profile.topics)                 if profile.topics              else None,
            json.dumps(profile.personality_offsets)  if profile.personality_offsets else None,
            json.dumps(profile.important_facts)      if profile.important_facts     else None,
            profile.relationship_damage,
            json.dumps(profile.important_quotes)     if profile.important_quotes    else None,
            json.dumps(profile.semantic_facts)       if profile.semantic_facts      else None,
        )
        cols = """(user_id, emotional_state, interaction_count, communication_style,
                   first_seen, last_seen, topics, personality_traits, important_facts,
                   relationship_damage, important_quotes, semantic_facts)"""

        if _DATABASE_URL:
            sql = f"""
                INSERT INTO user_profiles {cols} VALUES ({_ph(12)})
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
            """
        else:
            sql = f"INSERT OR REPLACE INTO user_profiles {cols} VALUES ({_ph(12)})"

        with _cursor() as (cur, conn):
            cur.execute(sql, params)
            conn.commit()

    def load_user_profile(self, user_id: str) -> Optional[UserProfile]:
        sql = f"""
            SELECT user_id, emotional_state, interaction_count, communication_style,
                   first_seen, last_seen, topics, personality_traits, important_facts,
                   relationship_damage, important_quotes, semantic_facts
            FROM user_profiles WHERE user_id = {_ph(1)}
        """
        with _cursor() as (cur, _):
            cur.execute(sql, (user_id,))
            row = cur.fetchone()

        if not row:
            return None

        return UserProfile.from_dict({
            "user_id":             row[0],
            "emotional_state":     json.loads(row[1])  if row[1]  else None,
            "interaction_count":   row[2],
            "communication_style": row[3],
            "first_seen":          row[4],
            "last_seen":           row[5],
            "topics":              [t.strip() for t in row[6].split(",") if t.strip()] if row[6] else [],
            "personality_traits":  json.loads(row[7])  if row[7]  else {},
            "important_facts":     json.loads(row[8])  if row[8]  else {},
            "relationship_damage": row[9]              if row[9] is not None else 0.0,
            "important_quotes":    json.loads(row[10]) if row[10] else [],
            "semantic_facts":      json.loads(row[11]) if row[11] else {},
        })

    # ----------------------------------------------------------
    # STATS
    # ----------------------------------------------------------

    def get_average_sentiment_for_user(self, user_id: str) -> float:
        sql = f"SELECT AVG(sentiment) FROM interactions WHERE user_id = {_ph(1)}"
        with _cursor() as (cur, _):
            cur.execute(sql, (user_id,))
            result = cur.fetchone()[0]
        return float(result) if result is not None else 0.0

    # ----------------------------------------------------------
    # SESSIONS
    # ----------------------------------------------------------

    def save_session(
        self,
        user_id: str,
        topics: List[str],
        important_facts: dict,
        session_count: int,
        last_session_tone: str = "neutral",
    ):
        params = (
            user_id, datetime.now().isoformat(), session_count,
            ",".join(topics[:10]) if topics else "",
            json.dumps(important_facts) if important_facts else "{}",
            last_session_tone,
        )
        cols = "(user_id, date, session_count, topics, important_facts, last_session_tone)"

        if _DATABASE_URL:
            sql = f"""
                INSERT INTO sessions {cols} VALUES ({_ph(6)})
                ON CONFLICT (user_id) DO UPDATE SET
                    date              = EXCLUDED.date,
                    session_count     = EXCLUDED.session_count,
                    topics            = EXCLUDED.topics,
                    important_facts   = EXCLUDED.important_facts,
                    last_session_tone = EXCLUDED.last_session_tone
            """
        else:
            sql = f"INSERT OR REPLACE INTO sessions {cols} VALUES ({_ph(6)})"

        with _cursor() as (cur, conn):
            cur.execute(sql, params)
            conn.commit()

    def load_last_session(self, user_id: str) -> Optional[dict]:
        sql = f"""
            SELECT date, session_count, topics, important_facts, last_session_tone
            FROM sessions WHERE user_id = {_ph(1)}
        """
        with _cursor() as (cur, _):
            cur.execute(sql, (user_id,))
            row = cur.fetchone()

        if not row:
            return None

        return {
            "date":              datetime.fromisoformat(row[0]),
            "session_count":     row[1],
            "topics":            [t.strip() for t in row[2].split(",") if t.strip()] if row[2] else [],
            "important_facts":   json.loads(row[3]) if row[3] else {},
            "last_session_tone": row[4] if row[4] else "neutral",
        }