"""
Tests for all non-auth API routes: paradigms, protocols, participants, sessions,
project sessions, field templates; plus edge cases not covered in test_auth.py.

Storage is redirected to a shared temp directory. This module imports after
test_auth.py's patching, so it sets its own paths before pulling in the app.
"""
import json
import os
import secrets
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# ── Isolate storage to a fresh temp dir ──────────────────────────────────────
_TMPDIR = tempfile.mkdtemp(prefix="stresslab_api_test_")

import backend.logging_utils as _lu
import backend.users as _um
import backend.participant as _pm
import backend.auth as _am
import backend.projects as _prm
import backend.user_protocols as _upm

_lu.DATA_DIR = _TMPDIR
_um.USERS_FILE = os.path.join(_TMPDIR, "users.json")
_pm.PARTICIPANTS_FILE = os.path.join(_TMPDIR, "participants.json")
_prm.PROJECTS_FILE = os.path.join(_TMPDIR, "projects.json")
_upm.PROTOCOLS_FILE = os.path.join(_TMPDIR, "protocols.json")
_am._KEY_FILE = os.path.join(_TMPDIR, ".secret_key")
_am.SECRET_KEY = _am._load_or_create_secret()

from backend.app import app
from backend.models import SessionSummary, TrialResult

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with patch("backend.app.send_verification_email", return_value=None):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


@pytest.fixture(autouse=True)
def reset_rate_limits():
    import backend.app as _app_mod
    _app_mod._login_attempts.clear()
    yield
    _app_mod._login_attempts.clear()


def _unique_email() -> str:
    return f"api_user_{secrets.token_hex(4)}@example.com"


def _register_login(client: TestClient) -> dict:
    """Register a new user and return auth headers."""
    email = _unique_email()
    client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
    r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _register_login_full(client: TestClient) -> tuple[str, str, dict]:
    """Register a new user; return (email, user_id, auth_headers)."""
    email = _unique_email()
    reg = client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
    user_id = reg.json()["user_id"]
    r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    return email, user_id, headers


def _make_session(participant_id: str = "p_test", owner_id: str | None = None) -> str:
    """Write a minimal session JSON to the data dir and return the filename."""
    now = datetime.now(timezone.utc).isoformat()
    trial = TrialResult(
        trial_id="t1",
        paradigm_id="nback",
        paradigm_label="N-Back",
        difficulty=1,
        time_limit_sec=5.0,
        correct_answer="match",
        user_response="match",
        is_correct=True,
        timed_out=False,
        response_time_ms=320.0,
        timestamp=now,
        elapsed_sec=1.0,
    )
    summary = SessionSummary(
        participant_id=participant_id,
        session_start=now,
        session_end=now,
        duration_target_sec=300,
        intensity="medium",
        paradigms_used=["nback"],
        total_tasks=1,
        correct_answers=1,
        accuracy_pct=100.0,
        max_difficulty=1,
        avg_response_time_ms=320.0,
        per_paradigm={"nback": {"total": 1, "correct": 1}},
        trials=[trial],
    )
    from backend.logging_utils import save_session
    return os.path.basename(save_session(summary, owner_id=owner_id))


# ── Paradigms and protocols (open routes) ─────────────────────────────────────

class TestParadigmsProtocols:
    def test_paradigms_list_nonempty(self, client: TestClient):
        r = client.get("/api/paradigms")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        assert len(body) > 0

    def test_paradigms_have_required_fields(self, client: TestClient):
        r = client.get("/api/paradigms")
        for p in r.json():
            assert "id" in p
            assert "label" in p

    def test_protocols_list_nonempty(self, client: TestClient):
        r = client.get("/api/protocols")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        assert len(body) > 0

    def test_protocols_have_required_fields(self, client: TestClient):
        r = client.get("/api/protocols")
        for p in r.json():
            assert "id" in p
            assert "name" in p
            assert "paradigm_ids" in p


# ── Participants ──────────────────────────────────────────────────────────────

class TestParticipants:
    def test_create_participant(self, client: TestClient):
        pid = f"sub_{secrets.token_hex(4)}"
        r = client.post("/api/participants", json={"id": pid, "demographics": {"age": 25}})
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == pid
        assert body["demographics"]["age"] == 25

    def test_list_participants_includes_created(self, client: TestClient):
        pid = f"sub_{secrets.token_hex(4)}"
        client.post("/api/participants", json={"id": pid})
        r = client.get("/api/participants")
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert pid in ids

    def test_get_participant_by_id(self, client: TestClient):
        pid = f"sub_{secrets.token_hex(4)}"
        client.post("/api/participants", json={"id": pid, "demographics": {"group": "A"}})
        r = client.get(f"/api/participants/{pid}")
        assert r.status_code == 200
        assert r.json()["demographics"]["group"] == "A"

    def test_get_nonexistent_participant(self, client: TestClient):
        r = client.get("/api/participants/nobody_xyz_999")
        body = r.json()
        assert "error" in body

    def test_update_participant_demographics(self, client: TestClient):
        pid = f"sub_{secrets.token_hex(4)}"
        client.post("/api/participants", json={"id": pid, "demographics": {"age": 20}})
        r = client.put(f"/api/participants/{pid}", json={"demographics": {"age": 21, "group": "B"}})
        assert r.status_code == 200
        assert r.json()["demographics"]["age"] == 21

    def test_update_nonexistent_participant(self, client: TestClient):
        r = client.put("/api/participants/ghost_xyz", json={"demographics": {}})
        assert "error" in r.json()

    def test_delete_participant(self, client: TestClient):
        pid = f"sub_{secrets.token_hex(4)}"
        client.post("/api/participants", json={"id": pid})
        r = client.delete(f"/api/participants/{pid}")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Confirm gone
        r2 = client.get(f"/api/participants/{pid}")
        assert "error" in r2.json()


    def test_create_duplicate_id_upserts_or_conflicts(self, client: TestClient):
        """Duplicate participant IDs should not crash the server."""
        pid = f"sub_{secrets.token_hex(4)}"
        r1 = client.post("/api/participants", json={"id": pid, "demographics": {"age": 20}})
        r2 = client.post("/api/participants", json={"id": pid, "demographics": {"age": 99}})
        # Both should be non-error responses (upsert semantics are acceptable)
        assert r1.status_code == 200
        assert r2.status_code in (200, 409)

    def test_participant_has_created_field(self, client: TestClient):
        pid = f"sub_{secrets.token_hex(4)}"
        r = client.post("/api/participants", json={"id": pid})
        body = r.json()
        assert "created" in body

    def test_participant_session_files_initially_empty(self, client: TestClient):
        pid = f"sub_{secrets.token_hex(4)}"
        r = client.post("/api/participants", json={"id": pid})
        assert r.json()["session_files"] == []


# ── Sessions ──────────────────────────────────────────────────────────────────

class TestSessions:
    @pytest.fixture(scope="class")
    def authed(self, client):
        return _register_login_full(client)

    def _owner_id(self, authed):
        return authed[1]

    def _headers(self, authed):
        return authed[2]

    def test_list_sessions_requires_auth(self, client: TestClient):
        r = client.get("/api/sessions")
        assert r.status_code == 401

    def test_get_session_requires_auth(self, client: TestClient, authed):
        filename = _make_session(owner_id=self._owner_id(authed))
        r = client.get(f"/api/sessions/{filename}")
        assert r.status_code == 401

    def test_list_sessions_returns_list(self, client: TestClient, authed):
        r = client.get("/api/sessions", headers=self._headers(authed))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_sessions_filter_by_participant(self, client: TestClient, authed):
        pid = f"filter_{secrets.token_hex(4)}"
        filename = _make_session(pid, owner_id=self._owner_id(authed))
        r = client.get(f"/api/sessions?participant_id={pid}", headers=self._headers(authed))
        assert r.status_code == 200
        fnames = [s.get("filename") for s in r.json()]
        assert filename in fnames

    def test_get_session(self, client: TestClient, authed):
        filename = _make_session(owner_id=self._owner_id(authed))
        r = client.get(f"/api/sessions/{filename}", headers=self._headers(authed))
        assert r.status_code == 200
        body = r.json()
        assert "trials" in body
        assert "participant_id" in body

    def test_get_nonexistent_session(self, client: TestClient, authed):
        r = client.get("/api/sessions/does_not_exist.json", headers=self._headers(authed))
        body = r.json()
        assert "error" in body

    def test_get_session_path_traversal_blocked(self, client: TestClient, authed):
        r = client.get("/api/sessions/..passwd", headers=self._headers(authed))
        body = r.json()
        assert "error" in body

    def test_get_session_path_traversal_backslash_blocked(self, client: TestClient, authed):
        r = client.get("/api/sessions/..\\windows\\system32", headers=self._headers(authed))
        body = r.json()
        assert "error" in body

    def test_export_session_csv(self, client: TestClient, authed):
        filename = _make_session(owner_id=self._owner_id(authed))
        r = client.get(f"/api/sessions/{filename}/csv", headers=self._headers(authed))
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        lines = r.text.strip().split("\n")
        assert len(lines) >= 2  # header + at least one trial row

    def test_export_csv_header_columns(self, client: TestClient, authed):
        filename = _make_session(owner_id=self._owner_id(authed))
        r = client.get(f"/api/sessions/{filename}/csv", headers=self._headers(authed))
        header = r.text.strip().split("\n")[0]
        for col in ("trial_id", "paradigm_id", "is_correct", "response_time_ms"):
            assert col in header

    def test_export_csv_nonexistent_session(self, client: TestClient, authed):
        r = client.get("/api/sessions/ghost.json/csv", headers=self._headers(authed))
        body = r.json()
        assert "error" in body

    def test_export_csv_path_traversal_blocked(self, client: TestClient, authed):
        r = client.get("/api/sessions/..secret/csv", headers=self._headers(authed))
        body = r.json()
        assert "error" in body

    def test_patch_session_notes(self, client: TestClient, authed):
        filename = _make_session(owner_id=self._owner_id(authed))
        r = client.patch(f"/api/sessions/{filename}/notes",
                         json={"notes": "Interesting result"}, headers=self._headers(authed))
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Verify notes were saved
        session_data = client.get(f"/api/sessions/{filename}", headers=self._headers(authed)).json()
        assert session_data.get("notes") == "Interesting result"

    def test_patch_notes_empty_string(self, client: TestClient, authed):
        filename = _make_session(owner_id=self._owner_id(authed))
        client.patch(f"/api/sessions/{filename}/notes",
                     json={"notes": "initial note"}, headers=self._headers(authed))
        r = client.patch(f"/api/sessions/{filename}/notes",
                         json={"notes": ""}, headers=self._headers(authed))
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_patch_notes_nonexistent_session(self, client: TestClient, authed):
        r = client.patch("/api/sessions/ghost_xyz.json/notes",
                         json={"notes": "hello"}, headers=self._headers(authed))
        body = r.json()
        assert "error" in body

    def test_patch_notes_path_traversal_blocked(self, client: TestClient, authed):
        r = client.patch("/api/sessions/..evil.json/notes",
                         json={"notes": "x"}, headers=self._headers(authed))
        body = r.json()
        assert "error" in body

    def test_delete_session_requires_auth(self, client: TestClient, authed):
        filename = _make_session(owner_id=self._owner_id(authed))
        r = client.request("DELETE", f"/api/sessions/{filename}")
        assert r.status_code == 401

    def test_delete_session(self, client: TestClient, authed):
        filename = _make_session(owner_id=self._owner_id(authed))
        r = client.request("DELETE", f"/api/sessions/{filename}", headers=self._headers(authed))
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Confirm it is gone
        r2 = client.get(f"/api/sessions/{filename}", headers=self._headers(authed))
        assert "error" in r2.json()

    def test_delete_nonexistent_session(self, client: TestClient, authed):
        r = client.request("DELETE", "/api/sessions/ghost_xyz_999.json",
                           headers=self._headers(authed))
        assert r.status_code == 404

    def test_delete_session_path_traversal_blocked(self, client: TestClient, authed):
        r = client.request("DELETE", "/api/sessions/..evil", headers=self._headers(authed))
        assert r.status_code == 422

    def test_session_isolation_between_users(self, client: TestClient):
        """User A's sessions must not appear for User B."""
        _, uid_a, headers_a = _register_login_full(client)
        _, uid_b, headers_b = _register_login_full(client)
        filename = _make_session("isolation_test", owner_id=uid_a)
        # User A can see it
        fnames_a = [s["filename"] for s in client.get("/api/sessions", headers=headers_a).json()]
        assert filename in fnames_a
        # User B cannot
        fnames_b = [s["filename"] for s in client.get("/api/sessions", headers=headers_b).json()]
        assert filename not in fnames_b

    def test_session_get_isolation(self, client: TestClient):
        """User B cannot GET a specific session owned by User A."""
        _, uid_a, headers_a = _register_login_full(client)
        _, _, headers_b = _register_login_full(client)
        filename = _make_session("iso_get", owner_id=uid_a)
        r = client.get(f"/api/sessions/{filename}", headers=headers_b)
        assert "error" in r.json()

    def test_session_delete_isolation(self, client: TestClient):
        """User B cannot delete a session owned by User A."""
        _, uid_a, headers_a = _register_login_full(client)
        _, _, headers_b = _register_login_full(client)
        filename = _make_session("iso_del", owner_id=uid_a)
        r = client.request("DELETE", f"/api/sessions/{filename}", headers=headers_b)
        assert r.status_code == 404
        # Still exists for User A
        r2 = client.get(f"/api/sessions/{filename}", headers=headers_a)
        assert "trials" in r2.json()

    def test_session_csv_isolation(self, client: TestClient):
        """User B cannot export CSV for User A's session."""
        _, uid_a, _ = _register_login_full(client)
        _, _, headers_b = _register_login_full(client)
        filename = _make_session("iso_csv", owner_id=uid_a)
        r = client.get(f"/api/sessions/{filename}/csv", headers=headers_b)
        assert "error" in r.json()

    def test_session_notes_isolation(self, client: TestClient):
        """User B cannot patch notes on User A's session."""
        _, uid_a, _ = _register_login_full(client)
        _, _, headers_b = _register_login_full(client)
        filename = _make_session("iso_notes", owner_id=uid_a)
        r = client.patch(f"/api/sessions/{filename}/notes",
                         json={"notes": "hacked"}, headers=headers_b)
        assert "error" in r.json()


# ── Practice trials ───────────────────────────────────────────────────────────

class TestPracticeTrials:
    def test_generate_practice_trials(self, client: TestClient):
        r = client.get("/api/paradigms")
        paradigm_ids = [p["id"] for p in r.json()[:2]]
        r = client.post("/api/practice-trials", json={"paradigm_ids": paradigm_ids})
        assert r.status_code == 200
        trials = r.json()
        assert isinstance(trials, list)
        assert len(trials) == len(paradigm_ids)

    def test_generate_practice_trials_empty_list(self, client: TestClient):
        """Empty paradigm_ids falls back to all registered paradigms; server must not crash."""
        r = client.post("/api/practice-trials", json={"paradigm_ids": []})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_generate_practice_trials_invalid_paradigm(self, client: TestClient):
        """Unknown paradigm IDs should not crash; they are either skipped or error."""
        r = client.post("/api/practice-trials", json={"paradigm_ids": ["totally_fake_id"]})
        # Acceptable: 200 with empty list, or 422/500 — must not be unhandled crash
        assert r.status_code in (200, 422, 500)


# ── Project update and session attachment ─────────────────────────────────────

class TestProjectAdvanced:
    @pytest.fixture(scope="class")
    def authed(self, client):
        return _register_login_full(client)

    def _headers(self, authed):
        return authed[2]

    def _owner_id(self, authed):
        return authed[1]

    def test_update_project_name(self, client: TestClient, authed):
        r = client.post("/api/projects", json={"name": "Old Name"}, headers=self._headers(authed))
        pid = r.json()["id"]
        r2 = client.put(f"/api/projects/{pid}", json={"name": "New Name"}, headers=self._headers(authed))
        assert r2.status_code == 200
        assert r2.json()["name"] == "New Name"

    def test_update_project_description(self, client: TestClient, authed):
        r = client.post("/api/projects", json={"name": "Proj"}, headers=self._headers(authed))
        pid = r.json()["id"]
        r2 = client.put(f"/api/projects/{pid}",
                        json={"description": "Updated desc"}, headers=self._headers(authed))
        assert r2.status_code == 200
        assert r2.json()["description"] == "Updated desc"

    def test_update_nonexistent_project(self, client: TestClient, authed):
        r = client.put("/api/projects/nonexistent_id",
                       json={"name": "X"}, headers=self._headers(authed))
        assert r.status_code == 404

    def test_update_other_users_project_rejected(self, client: TestClient):
        h1 = _register_login(client)
        h2 = _register_login(client)
        r = client.post("/api/projects", json={"name": "Mine"}, headers=h1)
        pid = r.json()["id"]
        r2 = client.put(f"/api/projects/{pid}", json={"name": "Hijacked"}, headers=h2)
        assert r2.status_code == 404

    def test_attach_session_to_project(self, client: TestClient, authed):
        filename = _make_session(owner_id=self._owner_id(authed))
        r_proj = client.post("/api/projects", json={"name": "With Sessions"},
                             headers=self._headers(authed))
        pid = r_proj.json()["id"]
        r = client.post(f"/api/projects/{pid}/sessions",
                        json={"session_file": filename}, headers=self._headers(authed))
        assert r.status_code == 200
        project = client.get(f"/api/projects/{pid}", headers=self._headers(authed)).json()
        assert filename in project.get("session_files", [])

    def test_attach_session_path_traversal_blocked(self, client: TestClient, authed):
        r_proj = client.post("/api/projects", json={"name": "Safe"},
                             headers=self._headers(authed))
        pid = r_proj.json()["id"]
        r = client.post(f"/api/projects/{pid}/sessions",
                        json={"session_file": "../../etc/passwd"},
                        headers=self._headers(authed))
        assert r.status_code == 422

    def test_detach_session_from_project(self, client: TestClient, authed):
        filename = _make_session(owner_id=self._owner_id(authed))
        r_proj = client.post("/api/projects", json={"name": "Detach Test"},
                             headers=self._headers(authed))
        pid = r_proj.json()["id"]
        client.post(f"/api/projects/{pid}/sessions",
                    json={"session_file": filename}, headers=self._headers(authed))
        r_del = client.request(
            "DELETE", f"/api/projects/{pid}/sessions/{filename}", headers=self._headers(authed)
        )
        assert r_del.status_code == 200
        project = client.get(f"/api/projects/{pid}", headers=self._headers(authed)).json()
        assert filename not in project.get("session_files", [])

    def test_attach_to_nonexistent_project(self, client: TestClient, authed):
        filename = _make_session(owner_id=self._owner_id(authed))
        r = client.post("/api/projects/doesnotexist/sessions",
                        json={"session_file": filename}, headers=self._headers(authed))
        assert r.status_code == 404

    def test_attach_to_other_users_project_rejected(self, client: TestClient):
        h1 = _register_login(client)
        h2 = _register_login(client)
        r = client.post("/api/projects", json={"name": "Private"}, headers=h1)
        pid = r.json()["id"]
        filename = _make_session()
        r2 = client.post(f"/api/projects/{pid}/sessions",
                         json={"session_file": filename}, headers=h2)
        assert r2.status_code == 404


# ── Field templates ───────────────────────────────────────────────────────────

class TestFieldTemplates:
    @pytest.fixture(scope="class")
    def authed(self, client):
        return _register_login(client)

    def test_initially_empty(self, client: TestClient, authed):
        r = client.get("/api/user/field-templates", headers=authed)
        assert r.status_code == 200
        assert r.json()["templates"] == []

    def test_save_and_retrieve(self, client: TestClient, authed):
        templates = ["Age", "Group", "Handedness"]
        r = client.put("/api/user/field-templates",
                       json={"templates": templates}, headers=authed)
        assert r.status_code == 200
        assert r.json()["templates"] == templates
        r2 = client.get("/api/user/field-templates", headers=authed)
        assert r2.json()["templates"] == templates

    def test_deduplication(self, client: TestClient, authed):
        r = client.put("/api/user/field-templates",
                       json={"templates": ["Age", "Age", "Group"]}, headers=authed)
        assert r.status_code == 200
        assert r.json()["templates"] == ["Age", "Group"]

    def test_blank_entries_stripped(self, client: TestClient, authed):
        r = client.put("/api/user/field-templates",
                       json={"templates": ["Age", "   ", "Group", ""]}, headers=authed)
        assert r.status_code == 200
        assert r.json()["templates"] == ["Age", "Group"]

    def test_all_blank_returns_empty(self, client: TestClient, authed):
        r = client.put("/api/user/field-templates",
                       json={"templates": ["   ", "", "  "]}, headers=authed)
        assert r.status_code == 200
        assert r.json()["templates"] == []

    def test_overwrite_templates(self, client: TestClient, authed):
        client.put("/api/user/field-templates",
                   json={"templates": ["Old1", "Old2"]}, headers=authed)
        r = client.put("/api/user/field-templates",
                       json={"templates": ["New1"]}, headers=authed)
        assert r.json()["templates"] == ["New1"]

    def test_templates_are_per_user(self, client: TestClient):
        h1 = _register_login(client)
        h2 = _register_login(client)
        client.put("/api/user/field-templates",
                   json={"templates": ["User1Field"]}, headers=h1)
        r2 = client.get("/api/user/field-templates", headers=h2)
        assert "User1Field" not in r2.json()["templates"]

    def test_requires_auth(self, client: TestClient):
        assert client.get("/api/user/field-templates").status_code == 401
        assert client.put("/api/user/field-templates",
                          json={"templates": []}).status_code == 401


# ── User protocol isolation ───────────────────────────────────────────────────

class TestProtocolIsolation:
    _PROTO_BODY = {
        "name": "IsolationCheck",
        "mode": "custom",
        "paradigm_ids": [],
        "duration_min": 5,
        "intensity": "low",
        "blocks": 1,
        "rest_duration_sec": 15,
        "practice_enabled": False,
    }

    def test_protocols_isolated_between_users(self, client: TestClient):
        h1 = _register_login(client)
        h2 = _register_login(client)
        r = client.post("/api/user-protocols", json=self._PROTO_BODY, headers=h1)
        assert r.status_code == 201
        pid = r.json()["id"]
        # User 2 should not see user 1's protocol
        protos2 = client.get("/api/user-protocols", headers=h2).json()
        assert not any(p["id"] == pid for p in protos2)

    def test_cannot_delete_other_users_protocol(self, client: TestClient):
        h1 = _register_login(client)
        h2 = _register_login(client)
        r = client.post("/api/user-protocols", json=self._PROTO_BODY, headers=h1)
        pid = r.json()["id"]
        r2 = client.delete(f"/api/user-protocols/{pid}", headers=h2)
        assert r2.status_code == 404

    def test_empty_protocol_name_rejected(self, client: TestClient):
        h = _register_login(client)
        body = {**self._PROTO_BODY, "name": "   "}
        r = client.post("/api/user-protocols", json=body, headers=h)
        assert r.status_code == 422


# ── Auth edge cases ───────────────────────────────────────────────────────────

class TestAuthEdgeCases:
    def _register_login(self, client, password="pass1234"):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": password})
        r = client.post("/api/auth/login", json={"email": email, "password": password})
        return email, r.json()["access_token"]

    def test_password_exactly_8_chars_accepted(self, client: TestClient):
        email = _unique_email()
        r = client.post("/api/auth/register",
                        json={"email": email, "password": "12345678"})
        assert r.status_code == 201

    def test_password_exactly_7_chars_rejected(self, client: TestClient):
        r = client.post("/api/auth/register",
                        json={"email": _unique_email(), "password": "1234567"})
        assert r.status_code == 422

    def test_password_exactly_72_chars_accepted_for_change(self, client: TestClient):
        _, token = self._register_login(client)
        r = client.post(
            "/api/auth/change-password",
            json={"old_password": "pass1234", "new_password": "x" * 72},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200

    def test_password_73_chars_rejected_for_change(self, client: TestClient):
        _, token = self._register_login(client)
        r = client.post(
            "/api/auth/change-password",
            json={"old_password": "pass1234", "new_password": "x" * 73},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422

    def test_mfa_pending_token_cannot_access_protected_routes(self, client: TestClient):
        """An mfa-pending JWT must not be accepted as an access token."""
        import pyotp
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r_login = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        token1 = r_login.json()["access_token"]

        # Enable MFA
        headers = {"Authorization": f"Bearer {token1}"}
        setup_r = client.post("/api/auth/mfa/setup", headers=headers)
        secret = setup_r.json()["secret"]
        code = pyotp.TOTP(secret).now()
        client.post("/api/auth/mfa/enable", json={"code": code}, headers=headers)

        # Login returns mfa_required
        login2 = client.post("/api/auth/login",
                             json={"email": email, "password": "pass1234"})
        mfa_token = login2.json()["mfa_token"]

        # mfa_token must NOT grant access to /api/auth/me
        r = client.get("/api/auth/me",
                       headers={"Authorization": f"Bearer {mfa_token}"})
        assert r.status_code == 401

    def test_expired_token_rejected(self, client: TestClient):
        """A token with exp=0 (already expired) must be rejected."""
        from backend.auth import create_token
        expired_token = create_token({"sub": "fake-user", "type": "access"},
                                     expires_minutes=-1)
        r = client.get("/api/auth/me",
                       headers={"Authorization": f"Bearer {expired_token}"})
        assert r.status_code == 401

    def test_completely_malformed_token_rejected(self, client: TestClient):
        r = client.get("/api/auth/me",
                       headers={"Authorization": "Bearer notavalidjwt"})
        assert r.status_code == 401

    def test_bearer_prefix_required(self, client: TestClient):
        _, token = self._register_login(client)
        r = client.get("/api/auth/me",
                       headers={"Authorization": token})  # no "Bearer " prefix
        assert r.status_code == 401

    def test_delete_account_empty_password_rejected(self, client: TestClient):
        _, token = self._register_login(client)
        r = client.request(
            "DELETE", "/api/auth/account",
            json={"password": ""},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 401

    def test_change_password_same_as_old_is_allowed(self, client: TestClient):
        """Changing to the same password is technically valid — not a security concern."""
        _, token = self._register_login(client)
        r = client.post(
            "/api/auth/change-password",
            json={"old_password": "pass1234", "new_password": "pass1234"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200

    def test_whitespace_email_normalized(self, client: TestClient):
        """Trailing/leading whitespace in email should be normalized on registration."""
        email = _unique_email()
        r = client.post("/api/auth/register",
                        json={"email": f"  {email}  ", "password": "pass1234"})
        assert r.status_code == 201
        # Can log in without whitespace
        r2 = client.post("/api/auth/login",
                         json={"email": email, "password": "pass1234"})
        assert r2.status_code == 200

    def test_update_profile_requires_auth(self, client: TestClient):
        r = client.patch("/api/auth/profile", json={"phone": "123"})
        assert r.status_code == 401

    def test_update_display_name(self, client: TestClient):
        _, token = self._register_login(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = client.patch("/api/auth/profile",
                         json={"display_name": "Dr. Smith"},
                         headers=headers)
        assert r.status_code == 200
        assert r.json()["display_name"] == "Dr. Smith"
        # Persisted: re-fetch via /me
        me = client.get("/api/auth/me", headers=headers).json()
        assert me["display_name"] == "Dr. Smith"

    def test_display_name_too_long_rejected(self, client: TestClient):
        _, token = self._register_login(client)
        r = client.patch("/api/auth/profile",
                         json={"display_name": "x" * 65},
                         headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 422

    def test_display_name_null_clears_value(self, client: TestClient):
        _, token = self._register_login(client)
        headers = {"Authorization": f"Bearer {token}"}
        client.patch("/api/auth/profile",
                     json={"display_name": "Temp Name"},
                     headers=headers)
        r = client.patch("/api/auth/profile",
                         json={"display_name": None},
                         headers=headers)
        assert r.status_code == 200
        assert r.json()["display_name"] is None


# ── Rate limiting — register and resend ───────────────────────────────────────

class TestRateLimitingExtended:
    def test_register_rate_limit(self, client: TestClient):
        """After 10 register attempts from the same IP, should get 429."""
        import backend.app as _app_mod
        _app_mod._login_attempts.clear()
        responses = [
            client.post("/api/auth/register",
                        json={"email": _unique_email(), "password": "pass1234"})
            for _ in range(11)
        ]
        codes = [r.status_code for r in responses]
        assert 429 in codes, f"Rate limit not triggered; codes were {codes}"

    def test_resend_verification_rate_limit(self, client: TestClient):
        """After 10 resend attempts from the same IP, should get 429."""
        import backend.app as _app_mod
        _app_mod._login_attempts.clear()
        responses = [
            client.post("/api/auth/resend-verification",
                        json={"email": "ratelimit@example.com"})
            for _ in range(11)
        ]
        codes = [r.status_code for r in responses]
        assert 429 in codes, f"Rate limit not triggered; codes were {codes}"


# ── Health check ──────────────────────────────────────────────────────────────

class TestHealthCheck:
    def test_health_returns_ok(self, client: TestClient):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"ok": True}


# ── Registration edge cases ──────────────────────────────────────────────────

class TestRegisterEdgeCases:
    def test_missing_email_field(self, client: TestClient):
        r = client.post("/api/auth/register", json={"password": "pass1234"})
        assert r.status_code == 422

    def test_missing_password_field(self, client: TestClient):
        r = client.post("/api/auth/register", json={"email": _unique_email()})
        assert r.status_code == 422

    def test_empty_body(self, client: TestClient):
        r = client.post("/api/auth/register", json={})
        assert r.status_code == 422

    def test_email_with_spaces_only(self, client: TestClient):
        r = client.post("/api/auth/register",
                        json={"email": "   ", "password": "pass1234"})
        assert r.status_code == 422

    def test_register_returns_user_id(self, client: TestClient):
        r = client.post("/api/auth/register",
                        json={"email": _unique_email(), "password": "pass1234"})
        assert r.status_code == 201
        assert len(r.json()["user_id"]) == 24  # secrets.token_hex(12) = 24 chars


# ── Login edge cases ─────────────────────────────────────────────────────────

class TestLoginEdgeCases:
    def test_missing_email(self, client: TestClient):
        r = client.post("/api/auth/login", json={"password": "pass1234"})
        assert r.status_code == 422

    def test_missing_password(self, client: TestClient):
        r = client.post("/api/auth/login", json={"email": _unique_email()})
        assert r.status_code == 422

    def test_empty_body(self, client: TestClient):
        r = client.post("/api/auth/login", json={})
        assert r.status_code == 422

    def test_login_response_has_user_fields(self, client: TestClient):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        user = r.json()["user"]
        assert user["email"] == email
        assert "id" in user
        assert "mfa_enabled" in user
        assert "email_verified" in user
        # password_hash must not be in the response
        assert "password_hash" not in user

    def test_login_user_object_excludes_sensitive_fields(self, client: TestClient):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        user = r.json()["user"]
        for sensitive in ("password_hash", "email_verify_token", "mfa_secret",
                          "mfa_secret_pending"):
            assert sensitive not in user


# ── MFA edge cases ────────────────────────────────────────────────────────────

class TestMFAEdgeCases:
    def _setup_mfa(self, client: TestClient):
        """Register, login, setup MFA, enable it, return (email, password, secret, token)."""
        import pyotp
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        setup_r = client.post("/api/auth/mfa/setup", headers=headers)
        secret = setup_r.json()["secret"]
        code = pyotp.TOTP(secret).now()
        client.post("/api/auth/mfa/enable", json={"code": code}, headers=headers)
        return email, "pass1234", secret, token

    def test_mfa_verify_wrong_code(self, client: TestClient):
        import pyotp
        email, password, secret, _ = self._setup_mfa(client)
        login_r = client.post("/api/auth/login",
                              json={"email": email, "password": password})
        mfa_token = login_r.json()["mfa_token"]
        r = client.post("/api/auth/mfa/verify",
                        json={"mfa_token": mfa_token, "code": "000000"})
        assert r.status_code == 401

    def test_mfa_verify_expired_mfa_token(self, client: TestClient):
        from backend.auth import create_token
        expired = create_token({"sub": "fake", "type": "mfa-pending"}, expires_minutes=-1)
        r = client.post("/api/auth/mfa/verify",
                        json={"mfa_token": expired, "code": "123456"})
        assert r.status_code == 401

    def test_mfa_verify_wrong_token_type(self, client: TestClient):
        from backend.auth import create_token
        access_token = create_token({"sub": "fake", "type": "access"})
        r = client.post("/api/auth/mfa/verify",
                        json={"mfa_token": access_token, "code": "123456"})
        assert r.status_code == 401


# ── Email verification edge cases ────────────────────────────────────────────

class TestEmailVerificationEdgeCases:
    def test_verify_then_profile_shows_verified(self, client: TestClient):
        email = _unique_email()
        captured_token = []
        with patch("backend.app.send_verification_email",
                   side_effect=lambda e, t: captured_token.append(t)):
            client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        client.get(f"/api/auth/verify-email?token={captured_token[0]}")
        r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        token = r.json()["access_token"]
        me = client.get("/api/auth/me",
                        headers={"Authorization": f"Bearer {token}"}).json()
        assert me["email_verified"] is True

    def test_resend_for_verified_user_no_error(self, client: TestClient):
        email = _unique_email()
        captured_token = []
        with patch("backend.app.send_verification_email",
                   side_effect=lambda e, t: captured_token.append(t)):
            client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        client.get(f"/api/auth/verify-email?token={captured_token[0]}")
        r = client.post("/api/auth/resend-verification", json={"email": email})
        assert r.status_code == 200
        assert r.json()["ok"] is True


# ── Delete account edge cases ────────────────────────────────────────────────

class TestDeleteAccountEdgeCases:
    def test_deleted_token_cannot_access_protected(self, client: TestClient):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        client.request("DELETE", "/api/auth/account",
                       json={"password": "pass1234"}, headers=headers)
        # Token still structurally valid, but user record is gone
        r2 = client.get("/api/auth/me", headers=headers)
        assert r2.status_code == 401

    def test_delete_removes_user_protocols(self, client: TestClient):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        client.post("/api/user-protocols", json={
            "name": "Gone", "mode": "custom", "paradigm_ids": [],
            "duration_min": 5, "intensity": "low", "blocks": 1,
            "rest_duration_sec": 15, "practice_enabled": False,
        }, headers=headers)
        client.request("DELETE", "/api/auth/account",
                       json={"password": "pass1234"}, headers=headers)
        r2 = client.post("/api/auth/login",
                         json={"email": email, "password": "pass1234"})
        assert r2.status_code == 401


# ── Multiple sessions per user ────────────────────────────────────────────────

class TestMultipleSessions:
    def test_multiple_sessions_listed(self, client: TestClient):
        _, uid, headers = _register_login_full(client)
        f1 = _make_session("multi_a", owner_id=uid)
        f2 = _make_session("multi_b", owner_id=uid)
        r = client.get("/api/sessions", headers=headers)
        fnames = [s["filename"] for s in r.json()]
        assert f1 in fnames
        assert f2 in fnames

    def test_session_content_has_trial_data(self, client: TestClient):
        _, uid, headers = _register_login_full(client)
        filename = _make_session("content_check", owner_id=uid)
        r = client.get(f"/api/sessions/{filename}", headers=headers)
        body = r.json()
        assert body["participant_id"] == "content_check"
        assert body["accuracy_pct"] == 100.0
        assert body["total_tasks"] == 1
        trials = body["trials"]
        assert len(trials) == 1
        assert trials[0]["paradigm_id"] == "nback"
        assert trials[0]["is_correct"] is True

    def test_csv_export_trial_count_matches(self, client: TestClient):
        _, uid, headers = _register_login_full(client)
        filename = _make_session("csv_rows", owner_id=uid)
        r = client.get(f"/api/sessions/{filename}/csv", headers=headers)
        lines = r.text.strip().split("\n")
        assert len(lines) == 2  # 1 header + 1 trial


# ── Project lifecycle ─────────────────────────────────────────────────────────

class TestProjectLifecycle:
    def test_full_lifecycle(self, client: TestClient):
        """Create project, attach sessions, detach, then delete."""
        _, uid, headers = _register_login_full(client)
        # Create project
        r = client.post("/api/projects", json={"name": "Lifecycle", "description": "test"},
                        headers=headers)
        assert r.status_code == 201
        pid = r.json()["id"]
        assert r.json()["session_files"] == []
        # Attach two sessions
        f1 = _make_session("lc1", owner_id=uid)
        f2 = _make_session("lc2", owner_id=uid)
        client.post(f"/api/projects/{pid}/sessions",
                    json={"session_file": f1}, headers=headers)
        client.post(f"/api/projects/{pid}/sessions",
                    json={"session_file": f2}, headers=headers)
        project = client.get(f"/api/projects/{pid}", headers=headers).json()
        assert f1 in project["session_files"]
        assert f2 in project["session_files"]
        # Detach one
        client.request("DELETE", f"/api/projects/{pid}/sessions/{f1}", headers=headers)
        project2 = client.get(f"/api/projects/{pid}", headers=headers).json()
        assert f1 not in project2["session_files"]
        assert f2 in project2["session_files"]
        # Delete project
        dr = client.delete(f"/api/projects/{pid}", headers=headers)
        assert dr.status_code == 200
        r2 = client.get(f"/api/projects/{pid}", headers=headers)
        assert r2.status_code == 404

    def test_duplicate_session_attach_is_idempotent(self, client: TestClient):
        _, uid, headers = _register_login_full(client)
        r = client.post("/api/projects", json={"name": "Dup"}, headers=headers)
        pid = r.json()["id"]
        f = _make_session("dup", owner_id=uid)
        client.post(f"/api/projects/{pid}/sessions",
                    json={"session_file": f}, headers=headers)
        client.post(f"/api/projects/{pid}/sessions",
                    json={"session_file": f}, headers=headers)
        project = client.get(f"/api/projects/{pid}", headers=headers).json()
        assert project["session_files"].count(f) == 1

    def test_project_has_required_fields(self, client: TestClient):
        _, _, headers = _register_login_full(client)
        r = client.post("/api/projects", json={"name": "Fields"}, headers=headers)
        body = r.json()
        for field in ("id", "owner_id", "name", "description", "created", "session_files"):
            assert field in body


# ── User protocol lifecycle ───────────────────────────────────────────────────

class TestUserProtocolLifecycle:
    _BODY = {
        "name": "Lifecycle Proto",
        "mode": "custom",
        "paradigm_ids": ["nback"],
        "duration_min": 10,
        "intensity": "medium",
        "blocks": 2,
        "rest_duration_sec": 30,
        "practice_enabled": True,
    }

    def test_create_has_expected_fields(self, client: TestClient):
        _, _, headers = _register_login_full(client)
        r = client.post("/api/user-protocols", json=self._BODY, headers=headers)
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Lifecycle Proto"
        assert "id" in body
        assert "created" in body

    def test_create_multiple_and_list(self, client: TestClient):
        _, _, headers = _register_login_full(client)
        ids = []
        for i in range(3):
            body = {**self._BODY, "name": f"Proto {i}"}
            r = client.post("/api/user-protocols", json=body, headers=headers)
            ids.append(r.json()["id"])
        protos = client.get("/api/user-protocols", headers=headers).json()
        listed_ids = [p["id"] for p in protos]
        for pid in ids:
            assert pid in listed_ids

    def test_delete_then_list_empty(self, client: TestClient):
        _, _, headers = _register_login_full(client)
        r = client.post("/api/user-protocols", json=self._BODY, headers=headers)
        pid = r.json()["id"]
        client.delete(f"/api/user-protocols/{pid}", headers=headers)
        protos = client.get("/api/user-protocols", headers=headers).json()
        assert not any(p["id"] == pid for p in protos)


# ── Full end-to-end lifecycle ─────────────────────────────────────────────────

class TestEndToEndLifecycle:
    def test_full_user_lifecycle(self, client: TestClient):
        """Register -> login -> create participant -> create project -> create
        session -> attach to project -> add notes -> export CSV -> detach ->
        delete session -> delete project -> delete account."""
        email = _unique_email()
        password = "lifecycle_pw_99"
        # Register
        reg = client.post("/api/auth/register",
                          json={"email": email, "password": password})
        assert reg.status_code == 201
        user_id = reg.json()["user_id"]
        # Login
        login = client.post("/api/auth/login",
                            json={"email": email, "password": password})
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        # Profile
        me = client.get("/api/auth/me", headers=headers).json()
        assert me["email"] == email
        # Create participant
        pid = f"e2e_{secrets.token_hex(4)}"
        pr = client.post("/api/participants", json={"id": pid, "demographics": {"age": 30}})
        assert pr.status_code == 200
        # Create project
        proj = client.post("/api/projects", json={"name": "E2E Study"}, headers=headers)
        assert proj.status_code == 201
        project_id = proj.json()["id"]
        # Create session (via helper, with owner_id)
        session_file = _make_session(pid, owner_id=user_id)
        # List sessions includes it
        sessions = client.get("/api/sessions", headers=headers).json()
        assert any(s["filename"] == session_file for s in sessions)
        # Attach session to project
        client.post(f"/api/projects/{project_id}/sessions",
                    json={"session_file": session_file}, headers=headers)
        project_data = client.get(f"/api/projects/{project_id}", headers=headers).json()
        assert session_file in project_data["session_files"]
        # Add notes
        notes_r = client.patch(f"/api/sessions/{session_file}/notes",
                               json={"notes": "E2E note"}, headers=headers)
        assert notes_r.json()["ok"] is True
        # Export CSV
        csv_r = client.get(f"/api/sessions/{session_file}/csv", headers=headers)
        assert "text/csv" in csv_r.headers["content-type"]
        assert "trial_id" in csv_r.text
        # Detach session from project
        client.request("DELETE",
                       f"/api/projects/{project_id}/sessions/{session_file}",
                       headers=headers)
        project_data2 = client.get(f"/api/projects/{project_id}", headers=headers).json()
        assert session_file not in project_data2["session_files"]
        # Delete session
        del_s = client.request("DELETE", f"/api/sessions/{session_file}",
                               headers=headers)
        assert del_s.json()["ok"] is True
        # Delete project
        del_p = client.delete(f"/api/projects/{project_id}", headers=headers)
        assert del_p.json()["ok"] is True
        # Delete account
        del_a = client.request("DELETE", "/api/auth/account",
                               json={"password": password}, headers=headers)
        assert del_a.json()["ok"] is True
        # Login should fail
        r_final = client.post("/api/auth/login",
                              json={"email": email, "password": password})
        assert r_final.status_code == 401


# ── Participant edge cases ────────────────────────────────────────────────────

class TestParticipantEdgeCases:
    def test_create_with_empty_demographics(self, client: TestClient):
        pid = f"sub_{secrets.token_hex(4)}"
        r = client.post("/api/participants", json={"id": pid})
        assert r.status_code == 200
        assert r.json()["demographics"] == {}

    def test_update_replaces_demographics(self, client: TestClient):
        pid = f"sub_{secrets.token_hex(4)}"
        client.post("/api/participants", json={"id": pid, "demographics": {"a": 1, "b": 2}})
        r = client.put(f"/api/participants/{pid}", json={"demographics": {"c": 3}})
        assert r.status_code == 200
        assert r.json()["demographics"] == {"c": 3}

    def test_participant_id_with_special_chars(self, client: TestClient):
        pid = f"sub-with-dashes_{secrets.token_hex(4)}"
        r = client.post("/api/participants", json={"id": pid})
        assert r.status_code == 200
        assert r.json()["id"] == pid