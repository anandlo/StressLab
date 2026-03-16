"""Project storage -- groups sessions under a named container.

Each user can own multiple projects. Each project holds a list of session
filenames (references to files in DATA_DIR, not copies).

Schema per project:
  {
    "id":            str   (24-char hex),
    "owner_id":      str   (user id),
    "name":          str,
    "description":   str,
    "created":       str   (ISO-8601),
    "session_files": [str, ...]
  }
"""
import json
import os
import secrets
from datetime import datetime

from .logging_utils import DATA_DIR
from . import db as _db

PROJECTS_FILE = os.path.join(DATA_DIR, "projects.json")


def _load() -> dict:
    if os.path.isfile(PROJECTS_FILE):
        with open(PROJECTS_FILE) as f:
            return json.load(f)
    return {}


def _save(data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PROJECTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _row_to_project(row: dict, files: list[str] | None = None) -> dict:
    return {
        "id": row["id"],
        "owner_id": row["owner_id"],
        "name": row["name"],
        "description": row["description"],
        "created": row["created"],
        "session_files": files if files is not None else [],
    }


def _get_session_files(cur, project_id: str) -> list[str]:
    cur.execute("SELECT filename FROM project_sessions WHERE project_id = %s", (project_id,))
    return [r["filename"] for r in cur.fetchall()]


def list_projects(owner_id: str) -> list[dict]:
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM projects WHERE owner_id = %s ORDER BY created", (owner_id,))
                rows = cur.fetchall()
                result = []
                for row in rows:
                    files = _get_session_files(cur, row["id"])
                    result.append(_row_to_project(row, files))
                return result
        finally:
            conn.close()
    return [p for p in _load().values() if p["owner_id"] == owner_id]


def get_project(project_id: str) -> dict | None:
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
                row = cur.fetchone()
                if not row:
                    return None
                files = _get_session_files(cur, project_id)
                return _row_to_project(row, files)
        finally:
            conn.close()
    return _load().get(project_id)


def create_project(owner_id: str, name: str, description: str = "") -> dict:
    pid = secrets.token_hex(12)
    project: dict = {
        "id": pid,
        "owner_id": owner_id,
        "name": name.strip(),
        "description": description.strip(),
        "created": datetime.now().isoformat(),
        "session_files": [],
    }
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO projects (id, owner_id, name, description, created) VALUES (%s, %s, %s, %s, %s)",
                    (pid, owner_id, project["name"], project["description"], project["created"])
                )
            conn.commit()
        finally:
            conn.close()
        return project
    db = _load()
    db[pid] = project
    _save(db)
    return project


def update_project(project_id: str, name: str | None = None, description: str | None = None) -> dict | None:
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                if name is not None and description is not None:
                    cur.execute("UPDATE projects SET name=%s, description=%s WHERE id=%s RETURNING *",
                                (name.strip(), description.strip(), project_id))
                elif name is not None:
                    cur.execute("UPDATE projects SET name=%s WHERE id=%s RETURNING *", (name.strip(), project_id))
                elif description is not None:
                    cur.execute("UPDATE projects SET description=%s WHERE id=%s RETURNING *",
                                (description.strip(), project_id))
                else:
                    cur.execute("SELECT * FROM projects WHERE id=%s", (project_id,))
                row = cur.fetchone()
                if not row:
                    return None
                files = _get_session_files(cur, project_id)
            conn.commit()
            return _row_to_project(row, files)
        finally:
            conn.close()
    db = _load()
    if project_id not in db:
        return None
    if name is not None:
        db[project_id]["name"] = name.strip()
    if description is not None:
        db[project_id]["description"] = description.strip()
    _save(db)
    return db[project_id]


def delete_project(project_id: str) -> bool:
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM projects WHERE id = %s RETURNING id", (project_id,))
                deleted = cur.fetchone()
            conn.commit()
            return deleted is not None
        finally:
            conn.close()
    db = _load()
    if project_id not in db:
        return False
    del db[project_id]
    _save(db)
    return True


def add_session_to_project(project_id: str, session_file: str) -> dict | None:
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO project_sessions (project_id, filename) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (project_id, session_file)
                )
            conn.commit()
            return get_project(project_id)
        finally:
            conn.close()
    db = _load()
    if project_id not in db:
        return None
    if session_file not in db[project_id]["session_files"]:
        db[project_id]["session_files"].append(session_file)
    _save(db)
    return db[project_id]


def remove_session_from_project(project_id: str, session_file: str) -> dict | None:
    if _db.DATABASE_URL:
        conn = _db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM project_sessions WHERE project_id = %s AND filename = %s",
                    (project_id, session_file)
                )
            conn.commit()
            return get_project(project_id)
        finally:
            conn.close()
    db = _load()
    if project_id not in db:
        return None
    db[project_id]["session_files"] = [
        f for f in db[project_id]["session_files"] if f != session_file
    ]
    _save(db)
    return db[project_id]
