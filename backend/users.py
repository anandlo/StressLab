"""User account storage.

When DATABASE_URL is set, data is stored in Postgres.
Otherwise falls back to a local JSON file for development.
"""
import json
import os
import secrets
from datetime import datetime

from .logging_utils import DATA_DIR
from . import db as _db

USERS_FILE = os.path.join(DATA_DIR, "users.json")


def _load() -> dict:
    if os.path.isfile(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}


def _save(data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Lookups ───────────────────────────────────────────────────────────────────

def get_user_by_email(email: str) -> dict | None:
    lo = email.strip().lower()
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE email = %s", (lo,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()
    db = _load()
    for user in db.values():
        if user["email"].lower() == lo:
            return user
    return None


def get_user_by_id(user_id: str) -> dict | None:
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()
    return _load().get(user_id)


# ── Mutations ─────────────────────────────────────────────────────────────────

def create_user(email: str, password_hash: str, phone: str | None = None) -> dict:
    user_id = secrets.token_hex(12)
    verify_token = secrets.token_urlsafe(32)
    user: dict = {
        "id": user_id,
        "email": email.strip().lower(),
        "phone": phone or None,
        "password_hash": password_hash,
        "email_verified": False,
        "email_verify_token": verify_token,
        "mfa_enabled": False,
        "mfa_secret": None,
        "created": datetime.now().isoformat(),
    }
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO users (id, email, phone, password_hash,
                       email_verified, email_verify_token, mfa_enabled, mfa_secret, created)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (user["id"], user["email"], user["phone"], user["password_hash"],
                     user["email_verified"], user["email_verify_token"],
                     user["mfa_enabled"], user["mfa_secret"], user["created"])
                )
            conn.commit()
        finally:
            conn.close()
        return user
    db = _load()
    db[user_id] = user
    _save(db)
    return user


def update_user(user_id: str, **kwargs) -> dict | None:
    if _db.DATABASE_URL:
        if not kwargs:
            return get_user_by_id(user_id)
        set_clause = ", ".join(f"{k} = %s" for k in kwargs)
        values = list(kwargs.values()) + [user_id]
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE users SET {set_clause} WHERE id = %s RETURNING *",
                    values
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None
        finally:
            conn.close()
    db = _load()
    if user_id not in db:
        return None
    db[user_id].update(kwargs)
    _save(db)
    return db[user_id]


def user_public(user: dict) -> dict:
    """Return only the fields safe to send to the client."""
    return {k: user[k] for k in ("id", "email", "phone", "mfa_enabled", "created")}


def consume_email_verify_token(token: str) -> bool:
    """Mark the matching user as email_verified. Returns True if successful."""
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users SET email_verified = TRUE, email_verify_token = NULL
                       WHERE email_verify_token = %s AND email_verified = FALSE
                       RETURNING id""",
                    (token,)
                )
                updated = cur.fetchone()
            conn.commit()
            return updated is not None
        finally:
            conn.close()
    db = _load()
    for user in db.values():
        if user.get("email_verify_token") == token and not user.get("email_verified"):
            user["email_verified"] = True
            user["email_verify_token"] = None
            _save(db)
            return True
    return False
