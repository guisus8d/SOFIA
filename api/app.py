# api/app.py
# ============================================================
# SocialBot — API + Panel Admin
# Sirve:
#   - index.html  (página pública de invitación)
#   - admin.html  (panel de administración)
#   - /static/    (imágenes)
#   - /api/       (endpoints para el panel)
# ============================================================

import os
import sqlite3
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIG
# ============================================================

# Contraseña del panel — defínela en tu .env como ADMIN_PASSWORD
ADMIN_USER     = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "sofia2025")  # cámbiala en producción
DB_PATH        = os.getenv("DATABASE_PATH", "data/bot_data.db")
VERSION        = "v0.9.3"

# Tokens de sesión en memoria (se limpian al reiniciar el servidor)
# Para producción real considera usar JWT o Redis, pero esto es suficiente por ahora
_active_tokens: dict[str, datetime] = {}
TOKEN_TTL_HOURS = 8

app = FastAPI(title="Sofía Admin API", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Archivos estáticos y páginas ──────────────────────────────
# Monta /static/ para las imágenes
if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================
# HELPERS DB
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ============================================================
# AUTENTICACIÓN
# ============================================================

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/login")
def login(req: LoginRequest):
    if req.username != ADMIN_USER or req.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = secrets.token_hex(32)
    _active_tokens[token] = datetime.now()
    return {"token": token}


def verify_token(request: Request):
    """Dependencia que verifica el Bearer token en cada ruta protegida."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")

    token = auth.removeprefix("Bearer ").strip()

    # Limpiar tokens viejos
    now = datetime.now()
    expired = [t for t, ts in _active_tokens.items() if now - ts > timedelta(hours=TOKEN_TTL_HOURS)]
    for t in expired:
        del _active_tokens[t]

    if token not in _active_tokens:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    # Renovar TTL en cada request
    _active_tokens[token] = now
    return token


# ============================================================
# PÁGINAS HTML
# ============================================================

@app.get("/")
def serve_index():
    if Path("index.html").exists():
        return FileResponse("index.html")
    return JSONResponse({"status": "ok", "message": "Sofía API corriendo"})


@app.get("/admin")
def serve_admin():
    if Path("admin.html").exists():
        return FileResponse("admin.html")
    raise HTTPException(status_code=404, detail="admin.html no encontrado")


# ============================================================
# API — STATS
# ============================================================

@app.get("/api/stats")
def get_stats(db: sqlite3.Connection = Depends(get_db), _=Depends(verify_token)):
    users_count = db.execute("SELECT COUNT(*) FROM user_profiles").fetchone()[0]
    inter_count = db.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
    avg_sent    = db.execute("SELECT AVG(sentiment) FROM interactions").fetchone()[0]

    return {
        "users":           users_count,
        "interactions":    inter_count,
        "avg_sentiment":   round(avg_sent, 3) if avg_sent is not None else 0.0,
    }


# ============================================================
# API — USUARIOS
# ============================================================

@app.get("/api/users")
def get_users(db: sqlite3.Connection = Depends(get_db), _=Depends(verify_token)):
    rows = db.execute("""
        SELECT user_id, emotional_state, interaction_count,
               communication_style, first_seen, last_seen,
               topics, relationship_damage
        FROM user_profiles
        ORDER BY last_seen DESC
    """).fetchall()

    result = []
    for r in rows:
        # Parsear emoción del JSON de estado emocional
        emo = "neutral"
        energy = 50.0
        trust  = 50.0
        if r["emotional_state"]:
            try:
                es = json.loads(r["emotional_state"])
                emo    = es.get("primary_emotion", "neutral")
                energy = es.get("energy", 50.0)
                trust  = es.get("trust",  50.0)
            except Exception:
                pass

        topics = [t.strip() for t in r["topics"].split(",") if t.strip()] if r["topics"] else []

        result.append({
            "user_id":             r["user_id"],
            "emotion":             emo,
            "energy":              round(energy, 1),
            "trust":               round(trust, 1),
            "damage":              round(r["relationship_damage"] or 0.0, 2),
            "count":               r["interaction_count"] or 0,
            "communication_style": r["communication_style"] or "neutral",
            "first_seen":          r["first_seen"],
            "last_seen":           r["last_seen"],
            "topics":              topics,
        })

    return result


@app.get("/api/users/{user_id}")
def get_user(user_id: str, db: sqlite3.Connection = Depends(get_db), _=Depends(verify_token)):
    row = db.execute("""
        SELECT * FROM user_profiles WHERE user_id = ?
    """, (user_id,)).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    emo = "neutral"
    energy = 50.0
    trust  = 50.0
    if row["emotional_state"]:
        try:
            es = json.loads(row["emotional_state"])
            emo    = es.get("primary_emotion", "neutral")
            energy = es.get("energy", 50.0)
            trust  = es.get("trust",  50.0)
        except Exception:
            pass

    topics  = [t.strip() for t in row["topics"].split(",") if t.strip()] if row["topics"] else []
    facts   = json.loads(row["important_facts"])   if row["important_facts"]   else {}
    quotes  = json.loads(row["important_quotes"])  if row["important_quotes"]  else []
    sem     = json.loads(row["semantic_facts"])    if row["semantic_facts"]    else {}

    return {
        "user_id":             row["user_id"],
        "emotion":             emo,
        "energy":              round(energy, 1),
        "trust":               round(trust, 1),
        "damage":              round(row["relationship_damage"] or 0.0, 2),
        "count":               row["interaction_count"] or 0,
        "communication_style": row["communication_style"] or "neutral",
        "first_seen":          row["first_seen"],
        "last_seen":           row["last_seen"],
        "topics":              topics,
        "important_facts":     facts,
        "important_quotes":    quotes,
        "semantic_facts":      sem,
    }


# ============================================================
# API — INTERACCIONES
# ============================================================

@app.get("/api/interactions")
def get_interactions(
    limit: int = 50,
    user_id: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
    _=Depends(verify_token),
):
    if user_id:
        rows = db.execute("""
            SELECT id, user_id, message, sentiment, response,
                   timestamp, emotion_before, emotion_after
            FROM interactions
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()
    else:
        rows = db.execute("""
            SELECT id, user_id, message, sentiment, response,
                   timestamp, emotion_before, emotion_after
            FROM interactions
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,)).fetchall()

    return [
        {
            "id":            r["id"],
            "user_id":       r["user_id"],
            "message":       r["message"],
            "sentiment":     round(r["sentiment"], 3) if r["sentiment"] is not None else None,
            "response":      r["response"],
            "timestamp":     r["timestamp"],
            "emotion_before": r["emotion_before"],
            "emotion_after":  r["emotion_after"],
        }
        for r in rows
    ]


# ============================================================
# API — INFO
# ============================================================

@app.get("/api/info")
def get_info(_=Depends(verify_token)):
    return {
        "version":  VERSION,
        "db_path":  DB_PATH,
        "db_exists": Path(DB_PATH).exists(),
    }


# ============================================================
# API — ACCIONES ADMIN
# ============================================================

@app.post("/api/admin/reset_sessions")
def reset_sessions(db: sqlite3.Connection = Depends(get_db), _=Depends(verify_token)):
    """Limpia la tabla sessions completa."""
    db.execute("DELETE FROM sessions")
    db.commit()
    return {"ok": True, "message": "Sesiones limpiadas"}


@app.post("/api/admin/purge_old")
def purge_old_interactions(db: sqlite3.Connection = Depends(get_db), _=Depends(verify_token)):
    """Elimina interacciones de más de 30 días."""
    cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    result = db.execute(
        "DELETE FROM interactions WHERE timestamp < ?", (cutoff,)
    )
    db.commit()
    return {"ok": True, "deleted": result.rowcount}


# ============================================================
# ARRANQUE LOCAL
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
