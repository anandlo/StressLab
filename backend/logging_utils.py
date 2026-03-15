import os
import json
from datetime import datetime
from .models import SessionSummary

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "..", "data")


def save_session(summary: SessionSummary) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"stress_session_{summary.participant_id}_{ts}.json"
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(summary.model_dump(), f, indent=2, default=str)
    return filepath


def list_sessions(participant_id: str | None = None) -> list[dict]:
    if not os.path.exists(DATA_DIR):
        return []
    sessions = []
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.startswith("stress_session_") or not fname.endswith(".json"):
            continue
        if participant_id and participant_id not in fname:
            continue
        filepath = os.path.join(DATA_DIR, fname)
        with open(filepath) as f:
            data = json.load(f)
        sessions.append({
            "filename": fname,
            "participant_id": data.get("participant_id"),
            "session_start": data.get("session_start"),
            "total_tasks": data.get("total_tasks"),
            "accuracy_pct": data.get("accuracy_pct"),
            "intensity": data.get("intensity"),
        })
    return sessions


def load_session(filename: str) -> dict | None:
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath) as f:
            return json.load(f)
    return None
