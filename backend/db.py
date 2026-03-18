"""Database connection management.

When DATABASE_URL is set (production/Render), uses Postgres via psycopg2.
When unset, all storage modules fall back to local JSON files (local dev).
"""
import os
import urllib.parse

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL: str | None = os.environ.get("DATABASE_URL")


class DatabaseUnavailable(Exception):
    """Raised when the database cannot be reached."""


def _connect_kwargs() -> dict:
    """Parse DATABASE_URL into psycopg2 keyword args, enforcing sslmode=require."""
    p = urllib.parse.urlparse(DATABASE_URL)
    kwargs: dict = {
        "host": p.hostname,
        "port": p.port or 5432,
        "dbname": p.path.lstrip("/"),
        "user": p.username,
        "password": urllib.parse.unquote(p.password or ""),
        "sslmode": "require",
        "connect_timeout": 5,
        "cursor_factory": RealDictCursor,
    }
    # Allow override via query string (e.g. ?sslmode=disable for local testing)
    qs = urllib.parse.parse_qs(p.query)
    if "sslmode" in qs:
        kwargs["sslmode"] = qs["sslmode"][0]
    return kwargs


def get_conn() -> psycopg2.extensions.connection:
    """Return a new psycopg2 connection. Caller must close it."""
    try:
        return psycopg2.connect(**_connect_kwargs())
    except psycopg2.OperationalError as exc:
        raise DatabaseUnavailable(str(exc)) from exc


def init_db() -> None:
    """Create all tables if they don't exist. No-op when DATABASE_URL is unset."""
    if not DATABASE_URL:
        return
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT,
                    password_hash TEXT NOT NULL,
                    email_verified BOOLEAN DEFAULT FALSE,
                    email_verify_token TEXT,
                    mfa_enabled BOOLEAN DEFAULT FALSE,
                    mfa_secret TEXT,
                    mfa_secret_pending TEXT,
                    field_templates JSONB DEFAULT '[]',
                    created TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS participants (
                    id TEXT PRIMARY KEY,
                    demographics JSONB DEFAULT '{}',
                    created TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    created TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS project_sessions (
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    filename TEXT NOT NULL,
                    PRIMARY KEY (project_id, filename)
                );

                CREATE TABLE IF NOT EXISTS user_protocols (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    config JSONB NOT NULL,
                    created TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    filename TEXT PRIMARY KEY,
                    participant_id TEXT NOT NULL,
                    session_start TEXT,
                    total_tasks INTEGER,
                    accuracy_pct FLOAT,
                    intensity TEXT,
                    data JSONB NOT NULL,
                    created TEXT NOT NULL
                );
            """)
            # Add columns introduced after initial deploy (safe on fresh DBs too)
            cur.execute("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret_pending TEXT;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS field_templates JSONB DEFAULT '[]';
                ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name TEXT;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token TEXT;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_expires TEXT;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verify_token_expires TEXT;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER DEFAULT 0;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS lockout_until TEXT;
                ALTER TABLE sessions ADD COLUMN IF NOT EXISTS owner_id TEXT;
            """)
        conn.commit()
    finally:
        conn.close()
