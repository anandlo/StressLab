"""User protocol storage.

Each user can save custom protocol configurations.
Persisted as a JSON file at DATA_DIR/user_protocols.json.

Schema:
  { "<user_id>": [ { "id": str, "name": str, "created": str, ...config... }, ... ] }
"""
import json
import os
import secrets
from datetime import datetime

from .logging_utils import DATA_DIR

PROTOCOLS_FILE = os.path.join(DATA_DIR, "user_protocols.json")


def _load() -> dict:
    if os.path.isfile(PROTOCOLS_FILE):
        with open(PROTOCOLS_FILE) as f:
            return json.load(f)
    return {}


def _save(db: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PROTOCOLS_FILE, "w") as f:
        json.dump(db, f, indent=2)


def list_user_protocols(user_id: str) -> list[dict]:
    db = _load()
    return list(db.get(user_id, []))


def create_user_protocol(user_id: str, name: str, config: dict) -> dict:
    db = _load()
    protocol = {
        "id": secrets.token_hex(8),
        "name": name.strip(),
        "created": datetime.now().isoformat(),
        **config,
    }
    if user_id not in db:
        db[user_id] = []
    db[user_id].append(protocol)
    _save(db)
    return protocol


def delete_user_protocol(user_id: str, protocol_id: str) -> bool:
    db = _load()
    if user_id not in db:
        return False
    before = len(db[user_id])
    db[user_id] = [p for p in db[user_id] if p["id"] != protocol_id]
    if len(db[user_id]) == before:
        return False
    _save(db)
    return True
