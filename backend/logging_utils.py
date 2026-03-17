import os
import json
from datetime import datetime
from .models import SessionSummary

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def _get_db():
    """Lazy import to avoid circular imports."""
    from . import db as _db
    return _db


def save_session(summary: SessionSummary, owner_id: str | None = None,
                 session_name: str | None = None) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if session_name:
        # Sanitize user-provided name: keep alphanumeric, dash, underscore
        safe = "".join(c if c.isalnum() or c in "-_ " else "" for c in session_name).strip().replace(" ", "_")
        filename = f"{safe}_{ts}.json" if safe else f"stress_session_{summary.participant_id}_{ts}.json"
    else:
        filename = f"stress_session_{summary.participant_id}_{ts}.json"
    _db = _get_db()
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            data = summary.model_dump()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO sessions (filename, participant_id, session_start,
                       total_tasks, accuracy_pct, intensity, data, created, owner_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (filename) DO NOTHING""",
                    (filename, summary.participant_id,
                     str(data.get("session_start", "")),
                     data.get("total_tasks"), data.get("accuracy_pct"),
                     data.get("intensity"), json.dumps(data, default=str),
                     datetime.now().isoformat(), owner_id)
                )
            conn.commit()
        finally:
            conn.close()
        return filename
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    data = summary.model_dump()
    if owner_id:
        data["_owner_id"] = owner_id
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return filepath


def list_sessions(participant_id: str | None = None, owner_id: str | None = None) -> list[dict]:
    # owner_id is required; without it we cannot enforce isolation.
    if not owner_id:
        return []
    _db = _get_db()
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                if participant_id:
                    cur.execute(
                        "SELECT filename, participant_id, session_start, total_tasks, accuracy_pct, intensity"
                        " FROM sessions WHERE participant_id = %s AND owner_id = %s ORDER BY created",
                        (participant_id, owner_id)
                    )
                else:
                    cur.execute(
                        "SELECT filename, participant_id, session_start, total_tasks, accuracy_pct, intensity"
                        " FROM sessions WHERE owner_id = %s ORDER BY created",
                        (owner_id,)
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
        # Strict ownership: only return sessions that belong to this user.
        if data.get("_owner_id") != owner_id:
            continue
        sessions.append({
            "filename": fname,
            "participant_id": data.get("participant_id"),
            "session_start": data.get("session_start"),
            "total_tasks": data.get("total_tasks"),
            "accuracy_pct": data.get("accuracy_pct"),
            "intensity": data.get("intensity"),
        })
    return sessions


def load_session(filename: str, owner_id: str | None = None) -> dict | None:
    if not owner_id:
        return None
    _db = _get_db()
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data FROM sessions WHERE filename = %s AND owner_id = %s",
                    (filename, owner_id)
                )
                row = cur.fetchone()
                return row["data"] if row else None
        finally:
            conn.close()
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath) as f:
            data = json.load(f)
        if data.get("_owner_id") != owner_id:
            return None
        return data
    return None


def delete_session(filename: str, owner_id: str | None = None) -> bool:
    """Delete a stored session. Returns True if it existed and was deleted."""
    if not owner_id:
        return False
    _db = _get_db()
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM sessions WHERE filename = %s AND owner_id = %s RETURNING filename",
                    (filename, owner_id)
                )
                deleted = cur.fetchone()
            conn.commit()
            return deleted is not None
        finally:
            conn.close()
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.isfile(filepath):
        with open(filepath) as f:
            data = json.load(f)
        if data.get("_owner_id") != owner_id:
            return False
        os.remove(filepath)
        return True
    return False


def patch_session_notes(filename: str, notes: str, owner_id: str | None = None) -> bool:
    """Update the notes field on a stored session. Returns True if found."""
    if not owner_id:
        return False
    _db = _get_db()
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE sessions SET data = data || %s::jsonb WHERE filename = %s AND owner_id = %s RETURNING filename",
                    (json.dumps({"notes": notes}), filename, owner_id)
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
    if data.get("_owner_id") != owner_id:
        return False
    data["notes"] = notes
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return True
