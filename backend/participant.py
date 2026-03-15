import os
import json
from datetime import datetime
from .models import Participant

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "..", "data")
PARTICIPANTS_FILE = os.path.join(DATA_DIR, "participants.json")


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_db() -> dict[str, dict]:
    if os.path.exists(PARTICIPANTS_FILE):
        with open(PARTICIPANTS_FILE) as f:
            return json.load(f)
    return {}


def _save_db(db: dict[str, dict]):
    _ensure_dir()
    with open(PARTICIPANTS_FILE, "w") as f:
        json.dump(db, f, indent=2)


def create_participant(participant_id: str, demographics: dict | None = None) -> Participant:
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
    db = _load_db()
    if participant_id in db:
        return Participant(**db[participant_id])
    return None


def list_participants() -> list[Participant]:
    db = _load_db()
    return [Participant(**v) for v in db.values()]


def add_session_file(participant_id: str, file_path: str):
    db = _load_db()
    if participant_id in db:
        db[participant_id].setdefault("session_files", []).append(file_path)
        _save_db(db)


def update_participant(participant_id: str, demographics: dict) -> Participant | None:
    db = _load_db()
    if participant_id not in db:
        return None
    db[participant_id]["demographics"] = demographics
    _save_db(db)
    return Participant(**db[participant_id])


def delete_participant(participant_id: str) -> bool:
    db = _load_db()
    if participant_id not in db:
        return False
    del db[participant_id]
    _save_db(db)
    return True
