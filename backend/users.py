"""User account storage.

Persisted as a JSON file alongside other data. Schema (each value):
  {
    "id":                 str   (24-char hex),
    "email":              str,
    "phone":              str | null,
    "password_hash":      str   (bcrypt),
    "email_verified":     bool,
    "email_verify_token": str | null,
    "mfa_enabled":        bool,
    "mfa_secret":         str | null  (base32 TOTP secret),
    "created":            str   (ISO-8601)
  }
"""
import json
import os
import secrets
from datetime import datetime

from .logging_utils import DATA_DIR

USERS_FILE = os.path.join(DATA_DIR, "users.json")


def _load() -> dict:
    if os.path.isfile(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}


def _save(db: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(db, f, indent=2)


# ── Lookups ───────────────────────────────────────────────────────────────────

def get_user_by_email(email: str) -> dict | None:
    db = _load()
    lo = email.strip().lower()
    for user in db.values():
        if user["email"].lower() == lo:
            return user
    return None


def get_user_by_id(user_id: str) -> dict | None:
    return _load().get(user_id)


# ── Mutations ─────────────────────────────────────────────────────────────────

def create_user(email: str, password_hash: str, phone: str | None = None) -> dict:
    db = _load()
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
    db[user_id] = user
    _save(db)
    return user


def update_user(user_id: str, **kwargs) -> dict | None:
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
    db = _load()
    for user in db.values():
        if user.get("email_verify_token") == token and not user.get("email_verified"):
            user["email_verified"] = True
            user["email_verify_token"] = None
            _save(db)
            return True
    return False
