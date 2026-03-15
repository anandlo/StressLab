"""Database connection management.

When DATABASE_URL is set (production/Render), uses Postgres via psycopg2.
When unset, all storage modules fall back to local JSON files (local dev).
"""
import os

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL: str | None = os.environ.get("DATABASE_URL")


def get_conn() -> psycopg2.extensions.connection:
    """Return a new psycopg2 connection. Caller must close it."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


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
            """)
        conn.commit()
    finally:
        conn.close()
