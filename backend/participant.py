import json
import os
from datetime import datetime
from .models import Participant
from .logging_utils import DATA_DIR
from . import db as _db

PARTICIPANTS_FILE = os.path.join(DATA_DIR, "participants.json")


def _load_db() -> dict[str, dict]:
    if os.path.exists(PARTICIPANTS_FILE):
        with open(PARTICIPANTS_FILE) as f:
            return json.load(f)
    return {}


def _save_db(db: dict[str, dict]):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PARTICIPANTS_FILE, "w") as f:
        json.dump(db, f, indent=2)


def create_participant(participant_id: str, demographics: dict | None = None) -> Participant:
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM participants WHERE id = %s", (participant_id,))
                row = cur.fetchone()
                if row:
                    return Participant(id=row["id"], created=row["created"],
                                      demographics=row["demographics"] or {})
                created = datetime.now().isoformat()
                demo = json.dumps(demographics or {})
                cur.execute(
                    "INSERT INTO participants (id, demographics, created) VALUES (%s, %s, %s)",
                    (participant_id, demo, created)
                )
            conn.commit()
            return Participant(id=participant_id, created=created,
                               demographics=demographics or {})
        finally:
            conn.close()
    db = _load_db()
    if participant_id in db:
        return Participant(**db[participant_id])
    p = Participant(
        id=participant_id,
        created=datetime.now().isoformat(),
        demographics=demographics or {},
    )
    db[participant_id] = p.model_dump()
    _save_db(db)
    return p


def get_participant(participant_id: str) -> Participant | None:
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM participants WHERE id = %s", (participant_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return Participant(id=row["id"], created=row["created"],
                                   demographics=row["demographics"] or {})
        finally:
            conn.close()
    db = _load_db()
    if participant_id in db:
        return Participant(**db[participant_id])
    return None


def list_participants() -> list[Participant]:
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM participants ORDER BY created")
                rows = cur.fetchall()
                return [Participant(id=r["id"], created=r["created"],
                                    demographics=r["demographics"] or {}) for r in rows]
        finally:
            conn.close()
    return [Participant(**v) for v in _load_db().values()]


def add_session_file(participant_id: str, file_path: str):
    # session files are tracked in the sessions table in Postgres
    if _db.DATABASE_URL:
        return
    db = _load_db()
    if participant_id in db:
        db[participant_id].setdefault("session_files", []).append(file_path)
        _save_db(db)


def update_participant(participant_id: str, demographics: dict) -> Participant | None:
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE participants SET demographics = %s WHERE id = %s RETURNING *",
                    (json.dumps(demographics), participant_id)
                )
                row = cur.fetchone()
            conn.commit()
            if not row:
                return None
            return Participant(id=row["id"], created=row["created"],
                               demographics=row["demographics"] or {})
        finally:
            conn.close()
    db = _load_db()
    if participant_id not in db:
        return None
    db[participant_id]["demographics"] = demographics
    _save_db(db)
    return Participant(**db[participant_id])


def delete_participant(participant_id: str) -> bool:
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM participants WHERE id = %s RETURNING id", (participant_id,))
                deleted = cur.fetchone()
            conn.commit()
            return deleted is not None
        finally:
            conn.close()
    db = _load_db()
    if participant_id not in db:
        return False
    del db[participant_id]
    _save_db(db)
    return True
