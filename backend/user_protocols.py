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
from . import db as _db

PROTOCOLS_FILE = os.path.join(DATA_DIR, "user_protocols.json")


def _load() -> dict:
    if os.path.isfile(PROTOCOLS_FILE):
        with open(PROTOCOLS_FILE) as f:
            return json.load(f)
    return {}


def _save(data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PROTOCOLS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def list_user_protocols(user_id: str) -> list[dict]:
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM user_protocols WHERE user_id = %s ORDER BY created", (user_id,))
                rows = cur.fetchall()
                return [{"id": r["id"], "name": r["name"], "created": r["created"],
                         **r["config"]} for r in rows]
        finally:
            conn.close()
    return list(_load().get(user_id, []))


def create_user_protocol(user_id: str, name: str, config: dict) -> dict:
    protocol_id = secrets.token_hex(8)
    created = datetime.now().isoformat()
    protocol = {
        "id": protocol_id,
        "name": name.strip(),
        "created": created,
        **config,
    }
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO user_protocols (id, user_id, name, config, created) VALUES (%s, %s, %s, %s, %s)",
                    (protocol_id, user_id, name.strip(), json.dumps(config), created)
                )
            conn.commit()
        finally:
            conn.close()
        return protocol
    db = _load()
    if user_id not in db:
        db[user_id] = []
    db[user_id].append(protocol)
    _save(db)
    return protocol


def delete_user_protocol(user_id: str, protocol_id: str) -> bool:
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_protocols WHERE id = %s AND user_id = %s RETURNING id",
                    (protocol_id, user_id)
                )
                deleted = cur.fetchone()
            conn.commit()
            return deleted is not None
        finally:
            conn.close()
    db = _load()
    if user_id not in db:
        return False
    before = len(db[user_id])
    db[user_id] = [p for p in db[user_id] if p["id"] != protocol_id]
    if len(db[user_id]) == before:
        return False
    _save(db)
    return True
