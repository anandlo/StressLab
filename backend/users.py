"""User account storage.

When DATABASE_URL is set, data is stored in Postgres.
Otherwise falls back to a local JSON file for development.
"""
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from .logging_utils import DATA_DIR
from . import db as _db

USERS_FILE = os.path.join(DATA_DIR, "users.json")

# Whitelist prevents callers from setting arbitrary column names in the dynamic
# UPDATE query, which would be a SQL injection vector.
_ALLOWED_USER_FIELDS = {
    "phone", "display_name", "password_hash", "email_verified", "email_verify_token",
    "mfa_enabled", "mfa_secret", "mfa_secret_pending", "field_templates",
    "password_reset_token", "password_reset_expires",
    "email_verify_token_expires", "token_version", "failed_login_attempts", "lockout_until",
}


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
    verify_token_expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    user: dict = {
        "id": user_id,
        "email": email.strip().lower(),
        "phone": phone or None,
        "display_name": None,
        "password_hash": password_hash,
        "email_verified": False,
        "email_verify_token": verify_token,
        "email_verify_token_expires": verify_token_expires,
        "mfa_enabled": False,
        "mfa_secret": None,
        "token_version": 0,
        "created": datetime.now().isoformat(),
    }
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO users (id, email, phone, display_name, password_hash,
                       email_verified, email_verify_token, email_verify_token_expires,
                       mfa_enabled, mfa_secret, token_version, created)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (user["id"], user["email"], user["phone"], user["display_name"],
                     user["password_hash"], user["email_verified"], user["email_verify_token"],
                     user["email_verify_token_expires"], user["mfa_enabled"], user["mfa_secret"],
                     user["token_version"], user["created"])
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
    invalid = set(kwargs.keys()) - _ALLOWED_USER_FIELDS
    if invalid:
        raise ValueError(f"Attempted update of disallowed user field(s): {invalid}")
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
    return {k: user.get(k) for k in ("id", "email", "phone", "display_name", "mfa_enabled", "email_verified", "created")}


def consume_email_verify_token(token: str) -> bool:
    """Mark the matching user as email_verified. Returns True if successful."""
    now = datetime.now(timezone.utc).isoformat()
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users
                       SET email_verified = TRUE,
                           email_verify_token = NULL,
                           email_verify_token_expires = NULL
                       WHERE email_verify_token = %s
                         AND email_verified = FALSE
                         AND (email_verify_token_expires IS NULL
                              OR email_verify_token_expires > %s)
                       RETURNING id""",
                    (token, now)
                )
                updated = cur.fetchone()
            conn.commit()
            return updated is not None
        finally:
            conn.close()
    db = _load()
    for user in db.values():
        if user.get("email_verify_token") == token and not user.get("email_verified"):
            expires = user.get("email_verify_token_expires")
            if expires and expires < now:
                return False
            user["email_verified"] = True
            user["email_verify_token"] = None
            user["email_verify_token_expires"] = None
            _save(db)
            return True
    return False


def get_user_by_reset_token(token: str) -> dict | None:
    """Look up a user by password reset token. Returns None if token is missing or expired."""
    from datetime import datetime, timezone
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM users WHERE password_reset_token = %s",
                    (token,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                user = dict(row)
        finally:
            conn.close()
    else:
        db = _load()
        user = None
        for u in db.values():
            if u.get("password_reset_token") == token:
                user = u
                break
        if not user:
            return None
    expires = user.get("password_reset_expires")
    if not expires or datetime.fromisoformat(expires) < datetime.now(timezone.utc):
        return None
    return user


def delete_user(user_id: str) -> bool:
    """Delete a user and all their owned data. Sessions are kept (research data).
    Returns True if the user existed and was deleted."""
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                # Cascade: project_sessions are deleted via FK ON DELETE CASCADE on projects
                cur.execute("DELETE FROM user_protocols WHERE user_id = %s", (user_id,))
                cur.execute("DELETE FROM projects WHERE owner_id = %s", (user_id,))
                cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
                deleted = cur.fetchone()
            conn.commit()
            return deleted is not None
        finally:
            conn.close()
    db = _load()
    if user_id not in db:
        return False
    del db[user_id]
    _save(db)
    return True
