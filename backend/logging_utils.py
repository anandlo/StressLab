import os
import json
from datetime import datetime
from .models import SessionSummary

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def _get_db():
    """Lazy import to avoid circular imports."""
    from . import db as _db
    return _db


def save_session(summary: SessionSummary) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"stress_session_{summary.participant_id}_{ts}.json"
    _db = _get_db()
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            data = summary.model_dump()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO sessions (filename, participant_id, session_start,
                       total_tasks, accuracy_pct, intensity, data, created)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (filename) DO NOTHING""",
                    (filename, summary.participant_id,
                     str(data.get("session_start", "")),
                     data.get("total_tasks"), data.get("accuracy_pct"),
                     data.get("intensity"), json.dumps(data, default=str),
                     datetime.now().isoformat())
                )
            conn.commit()
        finally:
            conn.close()
        return filename
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(summary.model_dump(), f, indent=2, default=str)
    return filepath


def list_sessions(participant_id: str | None = None) -> list[dict]:
    _db = _get_db()
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                if participant_id:
                    cur.execute(
                        "SELECT filename, participant_id, session_start, total_tasks, accuracy_pct, intensity"
                        " FROM sessions WHERE participant_id = %s ORDER BY created",
                        (participant_id,)
                    )
                else:
                    cur.execute(
                        "SELECT filename, participant_id, session_start, total_tasks, accuracy_pct, intensity"
                        " FROM sessions ORDER BY created"
                    )
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
    if not os.path.exists(DATA_DIR):
        return []
    sessions = []
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.startswith("stress_session_") or not fname.endswith(".json"):
            continue
        if participant_id and participant_id not in fname:
            continue
        filepath = os.path.join(DATA_DIR, fname)
        with open(filepath) as f:
            data = json.load(f)
        sessions.append({
            "filename": fname,
            "participant_id": data.get("participant_id"),
            "session_start": data.get("session_start"),
            "total_tasks": data.get("total_tasks"),
            "accuracy_pct": data.get("accuracy_pct"),
            "intensity": data.get("intensity"),
        })
    return sessions


def load_session(filename: str) -> dict | None:
    _db = _get_db()
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT data FROM sessions WHERE filename = %s", (filename,))
                row = cur.fetchone()
                return row["data"] if row else None
        finally:
            conn.close()
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath) as f:
            return json.load(f)
    return None


def delete_session(filename: str) -> bool:
    """Delete a stored session. Returns True if it existed and was deleted."""
    _db = _get_db()
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM sessions WHERE filename = %s RETURNING filename",
                    (filename,)
                )
                deleted = cur.fetchone()
            conn.commit()
            return deleted is not None
        finally:
            conn.close()
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.isfile(filepath):
        os.remove(filepath)
        return True
    return False


def patch_session_notes(filename: str, notes: str) -> bool:
    """Update the notes field on a stored session. Returns True if found."""
    _db = _get_db()
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE sessions SET data = data || %s::jsonb WHERE filename = %s RETURNING filename",
                    (json.dumps({"notes": notes}), filename)
                )
                updated = cur.fetchone()
            conn.commit()
            return updated is not None
        finally:
            conn.close()
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(filepath):
        return False
    with open(filepath) as f:
        data = json.load(f)
    data["notes"] = notes
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return True
