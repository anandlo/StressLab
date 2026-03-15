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

PROJECTS_FILE = os.path.join(DATA_DIR, "projects.json")


def _load() -> dict:
    if os.path.isfile(PROJECTS_FILE):
        with open(PROJECTS_FILE) as f:
            return json.load(f)
    return {}


def _save(db: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PROJECTS_FILE, "w") as f:
        json.dump(db, f, indent=2)


def list_projects(owner_id: str) -> list[dict]:
    return [p for p in _load().values() if p["owner_id"] == owner_id]


def get_project(project_id: str) -> dict | None:
    return _load().get(project_id)


def create_project(owner_id: str, name: str, description: str = "") -> dict:
    db = _load()
    pid = secrets.token_hex(12)
    project: dict = {
        "id": pid,
        "owner_id": owner_id,
        "name": name.strip(),
        "description": description.strip(),
        "created": datetime.now().isoformat(),
        "session_files": [],
    }
    db[pid] = project
    _save(db)
    return project


def update_project(project_id: str, name: str | None = None, description: str | None = None) -> dict | None:
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
    db = _load()
    if project_id not in db:
        return False
    del db[project_id]
    _save(db)
    return True


def add_session_to_project(project_id: str, session_file: str) -> dict | None:
    db = _load()
    if project_id not in db:
        return None
    if session_file not in db[project_id]["session_files"]:
        db[project_id]["session_files"].append(session_file)
    _save(db)
    return db[project_id]


def remove_session_from_project(project_id: str, session_file: str) -> dict | None:
    db = _load()
    if project_id not in db:
        return None
    db[project_id]["session_files"] = [
        f for f in db[project_id]["session_files"] if f != session_file
    ]
    _save(db)
    return db[project_id]
