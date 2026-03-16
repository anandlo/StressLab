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


def _make_session(participant_id: str = "p_test") -> str:
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
    return os.path.basename(save_session(summary))


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

    def test_delete_nonexistent_participant(self, client: TestClient):
        r = client.delete("/api/participants/nobody_abc_123")
        assert r.status_code == 200
        assert r.json()["ok"] is False

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
    def test_list_sessions_returns_list(self, client: TestClient):
        r = client.get("/api/sessions")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_sessions_filter_by_participant(self, client: TestClient):
        pid = f"filter_{secrets.token_hex(4)}"
        filename = _make_session(pid)
        r = client.get(f"/api/sessions?participant_id={pid}")
        assert r.status_code == 200
        fnames = [s.get("filename") for s in r.json()]
        assert filename in fnames

    def test_get_session(self, client: TestClient):
        filename = _make_session()
        r = client.get(f"/api/sessions/{filename}")
        assert r.status_code == 200
        body = r.json()
        assert "trials" in body
        assert "participant_id" in body

    def test_get_nonexistent_session(self, client: TestClient):
        r = client.get("/api/sessions/does_not_exist.json")
        body = r.json()
        assert "error" in body

    def test_get_session_path_traversal_blocked(self, client: TestClient):
        # Filename starting with .. is caught by the app-level traversal check
        r = client.get("/api/sessions/..passwd")
        body = r.json()
        assert "error" in body

    def test_get_session_path_traversal_backslash_blocked(self, client: TestClient):
        r = client.get("/api/sessions/..\\windows\\system32")
        body = r.json()
        assert "error" in body

    def test_export_session_csv(self, client: TestClient):
        filename = _make_session()
        r = client.get(f"/api/sessions/{filename}/csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        lines = r.text.strip().split("\n")
        assert len(lines) >= 2  # header + at least one trial row

    def test_export_csv_header_columns(self, client: TestClient):
        filename = _make_session()
        r = client.get(f"/api/sessions/{filename}/csv")
        header = r.text.strip().split("\n")[0]
        for col in ("trial_id", "paradigm_id", "is_correct", "response_time_ms"):
            assert col in header

    def test_export_csv_nonexistent_session(self, client: TestClient):
        r = client.get("/api/sessions/ghost.json/csv")
        body = r.json()
        assert "error" in body

    def test_export_csv_path_traversal_blocked(self, client: TestClient):
        r = client.get("/api/sessions/..secret/csv")
        body = r.json()
        assert "error" in body

    def test_patch_session_notes(self, client: TestClient):
        filename = _make_session()
        r = client.patch(f"/api/sessions/{filename}/notes", json={"notes": "Interesting result"})
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Verify notes were saved
        session_data = client.get(f"/api/sessions/{filename}").json()
        assert session_data.get("notes") == "Interesting result"

    def test_patch_notes_empty_string(self, client: TestClient):
        filename = _make_session()
        client.patch(f"/api/sessions/{filename}/notes", json={"notes": "initial note"})
        r = client.patch(f"/api/sessions/{filename}/notes", json={"notes": ""})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_patch_notes_nonexistent_session(self, client: TestClient):
        r = client.patch("/api/sessions/ghost_xyz.json/notes", json={"notes": "hello"})
        body = r.json()
        assert "error" in body

    def test_patch_notes_path_traversal_blocked(self, client: TestClient):
        r = client.patch("/api/sessions/..evil.json/notes", json={"notes": "x"})
        body = r.json()
        assert "error" in body

    def test_delete_session_requires_auth(self, client: TestClient):
        filename = _make_session()
        r = client.request("DELETE", f"/api/sessions/{filename}")
        assert r.status_code == 401

    def test_delete_session(self, client: TestClient):
        filename = _make_session()
        headers = _register_login(client)
        r = client.request("DELETE", f"/api/sessions/{filename}", headers=headers)
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Confirm it is gone
        r2 = client.get(f"/api/sessions/{filename}")
        assert "error" in r2.json()

    def test_delete_nonexistent_session(self, client: TestClient):
        headers = _register_login(client)
        r = client.request("DELETE", "/api/sessions/ghost_xyz_999.json",
                           headers=headers)
        assert r.status_code == 404

    def test_delete_session_path_traversal_blocked(self, client: TestClient):
        headers = _register_login(client)
        r = client.request("DELETE", "/api/sessions/..evil", headers=headers)
        assert r.status_code == 422


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
        return _register_login(client)

    def test_update_project_name(self, client: TestClient, authed):
        r = client.post("/api/projects", json={"name": "Old Name"}, headers=authed)
        pid = r.json()["id"]
        r2 = client.put(f"/api/projects/{pid}", json={"name": "New Name"}, headers=authed)
        assert r2.status_code == 200
        assert r2.json()["name"] == "New Name"

    def test_update_project_description(self, client: TestClient, authed):
        r = client.post("/api/projects", json={"name": "Proj"}, headers=authed)
        pid = r.json()["id"]
        r2 = client.put(f"/api/projects/{pid}",
                        json={"description": "Updated desc"}, headers=authed)
        assert r2.status_code == 200
        assert r2.json()["description"] == "Updated desc"

    def test_update_nonexistent_project(self, client: TestClient, authed):
        r = client.put("/api/projects/nonexistent_id",
                       json={"name": "X"}, headers=authed)
        assert r.status_code == 404

    def test_update_other_users_project_rejected(self, client: TestClient):
        h1 = _register_login(client)
        h2 = _register_login(client)
        r = client.post("/api/projects", json={"name": "Mine"}, headers=h1)
        pid = r.json()["id"]
        r2 = client.put(f"/api/projects/{pid}", json={"name": "Hijacked"}, headers=h2)
        assert r2.status_code == 404

    def test_attach_session_to_project(self, client: TestClient, authed):
        filename = _make_session()
        r_proj = client.post("/api/projects", json={"name": "With Sessions"},
                             headers=authed)
        pid = r_proj.json()["id"]
        r = client.post(f"/api/projects/{pid}/sessions",
                        json={"session_file": filename}, headers=authed)
        assert r.status_code == 200
        project = client.get(f"/api/projects/{pid}", headers=authed).json()
        assert filename in project.get("session_files", [])

    def test_attach_session_path_traversal_blocked(self, client: TestClient, authed):
        r_proj = client.post("/api/projects", json={"name": "Safe"},
                             headers=authed)
        pid = r_proj.json()["id"]
        r = client.post(f"/api/projects/{pid}/sessions",
                        json={"session_file": "../../etc/passwd"},
                        headers=authed)
        assert r.status_code == 422

    def test_detach_session_from_project(self, client: TestClient, authed):
        filename = _make_session()
        r_proj = client.post("/api/projects", json={"name": "Detach Test"},
                             headers=authed)
        pid = r_proj.json()["id"]
        client.post(f"/api/projects/{pid}/sessions",
                    json={"session_file": filename}, headers=authed)
        r_del = client.request(
            "DELETE", f"/api/projects/{pid}/sessions/{filename}", headers=authed
        )
        assert r_del.status_code == 200
        project = client.get(f"/api/projects/{pid}", headers=authed).json()
        assert filename not in project.get("session_files", [])

    def test_attach_to_nonexistent_project(self, client: TestClient, authed):
        filename = _make_session()
        r = client.post("/api/projects/doesnotexist/sessions",
                        json={"session_file": filename}, headers=authed)
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
