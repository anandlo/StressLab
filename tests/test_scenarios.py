"""
Comprehensive scenario and edge-case tests that complement test_auth.py
and test_api.py. Covers multi-step lifecycle flows, password boundary
conditions, cross-user isolation, data integrity after account deletion,
MFA re-enable cycles, and profile edge cases.

Storage: runs against JSON file fallback (DATABASE_URL is unset).
"""
import json
import os
import secrets
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# ── Isolate storage ──────────────────────────────────────────────────────────
_TMPDIR = tempfile.mkdtemp(prefix="stresslab_scenario_test_")

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
    return f"scenario_{secrets.token_hex(4)}@example.com"


def _register_login(client: TestClient, email=None, password="pass1234"):
    email = email or _unique_email()
    client.post("/api/auth/register", json={"email": email, "password": password})
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    return email, password, r.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_session(participant_id: str = "p_test", owner_id: str | None = None) -> str:
    now = datetime.now(timezone.utc).isoformat()
    trial = TrialResult(
        trial_id="t1", paradigm_id="nback", paradigm_label="N-Back",
        difficulty=1, time_limit_sec=5.0, correct_answer="match",
        user_response="match", is_correct=True, timed_out=False,
        response_time_ms=320.0, timestamp=now, elapsed_sec=1.0,
    )
    summary = SessionSummary(
        participant_id=participant_id, session_start=now, session_end=now,
        duration_target_sec=300, intensity="medium", paradigms_used=["nback"],
        total_tasks=1, correct_answers=1, accuracy_pct=100.0, max_difficulty=1,
        avg_response_time_ms=320.0,
        per_paradigm={"nback": {"total": 1, "correct": 1}}, trials=[trial],
    )
    from backend.logging_utils import save_session
    return os.path.basename(save_session(summary, owner_id=owner_id))


def _get_user_id(client: TestClient, token: str) -> str:
    me = client.get("/api/auth/me", headers=_headers(token))
    return me.json()["id"]


# ── Password edge cases ──────────────────────────────────────────────────────

class TestPasswordEdgeCases:
    def test_register_with_72_char_password(self, client: TestClient):
        email = _unique_email()
        pw = "A" * 72
        r = client.post("/api/auth/register", json={"email": email, "password": pw})
        assert r.status_code == 201
        r2 = client.post("/api/auth/login", json={"email": email, "password": pw})
        assert r2.status_code == 200

    def test_register_with_73_char_password_accepted_but_truncated(self, client: TestClient):
        """bcrypt silently truncates at 72 bytes. Registration should succeed,
        and login with the first 72 chars should also succeed because both
        sides truncate."""
        email = _unique_email()
        pw73 = "B" * 73
        r = client.post("/api/auth/register", json={"email": email, "password": pw73})
        # Registration succeeds (no upper limit enforced on register endpoint)
        assert r.status_code == 201
        # Login with the full 73-char password works because both sides truncate
        r2 = client.post("/api/auth/login", json={"email": email, "password": pw73})
        assert r2.status_code == 200
        # Login with just 72 chars also works (same truncation)
        r3 = client.post("/api/auth/login", json={"email": email, "password": "B" * 72})
        assert r3.status_code == 200

    def test_password_with_special_characters(self, client: TestClient):
        email = _unique_email()
        pw = "p@$$w0rd!#%^&*()"
        r = client.post("/api/auth/register", json={"email": email, "password": pw})
        assert r.status_code == 201
        r2 = client.post("/api/auth/login", json={"email": email, "password": pw})
        assert r2.status_code == 200

    def test_password_with_unicode(self, client: TestClient):
        email = _unique_email()
        pw = "passwort\u00fc\u00e4\u00f6\u00df\u2603"  # German chars + snowman
        r = client.post("/api/auth/register", json={"email": email, "password": pw})
        assert r.status_code == 201
        r2 = client.post("/api/auth/login", json={"email": email, "password": pw})
        assert r2.status_code == 200

    def test_password_with_spaces(self, client: TestClient):
        email = _unique_email()
        pw = "pass word with spaces"
        r = client.post("/api/auth/register", json={"email": email, "password": pw})
        assert r.status_code == 201
        r2 = client.post("/api/auth/login", json={"email": email, "password": pw})
        assert r2.status_code == 200

    def test_password_all_spaces_if_long_enough(self, client: TestClient):
        email = _unique_email()
        pw = "        "  # 8 spaces
        r = client.post("/api/auth/register", json={"email": email, "password": pw})
        assert r.status_code == 201
        r2 = client.post("/api/auth/login", json={"email": email, "password": pw})
        assert r2.status_code == 200

    def test_empty_password_rejected(self, client: TestClient):
        r = client.post("/api/auth/register",
                        json={"email": _unique_email(), "password": ""})
        assert r.status_code == 422

    def test_password_exactly_1_char_rejected(self, client: TestClient):
        r = client.post("/api/auth/register",
                        json={"email": _unique_email(), "password": "x"})
        assert r.status_code == 422


# ── Registration scenarios ────────────────────────────────────────────────────

class TestRegistrationScenarios:
    def test_reregister_after_account_deletion(self, client: TestClient):
        """Delete account then re-register with the same email."""
        email = _unique_email()
        pw = "original123"
        client.post("/api/auth/register", json={"email": email, "password": pw})
        r = client.post("/api/auth/login", json={"email": email, "password": pw})
        token = r.json()["access_token"]
        # Delete account
        client.request("DELETE", "/api/auth/account",
                       json={"password": pw}, headers=_headers(token))
        # Re-register with same email
        r2 = client.post("/api/auth/register", json={"email": email, "password": "newpass123"})
        assert r2.status_code == 201
        # Login with new password
        r3 = client.post("/api/auth/login", json={"email": email, "password": "newpass123"})
        assert r3.status_code == 200
        # Old password should not work
        r4 = client.post("/api/auth/login", json={"email": email, "password": pw})
        assert r4.status_code == 401

    def test_email_with_plus_alias(self, client: TestClient):
        """Emails with + alias should be accepted."""
        email = f"user+alias_{secrets.token_hex(4)}@example.com"
        r = client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        assert r.status_code == 201
        r2 = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        assert r2.status_code == 200

    def test_email_with_dots(self, client: TestClient):
        email = f"user.name.{secrets.token_hex(4)}@example.com"
        r = client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        assert r.status_code == 201

    def test_email_with_subdomain(self, client: TestClient):
        email = f"user_{secrets.token_hex(4)}@sub.domain.example.com"
        r = client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        assert r.status_code == 201

    def test_email_without_tld_rejected(self, client: TestClient):
        r = client.post("/api/auth/register",
                        json={"email": "user@localhost", "password": "pass1234"})
        assert r.status_code == 422

    def test_email_double_at_rejected(self, client: TestClient):
        r = client.post("/api/auth/register",
                        json={"email": "user@@example.com", "password": "pass1234"})
        assert r.status_code == 422

    def test_email_no_at_rejected(self, client: TestClient):
        r = client.post("/api/auth/register",
                        json={"email": "userexample.com", "password": "pass1234"})
        assert r.status_code == 422

    def test_long_email_accepted(self, client: TestClient):
        local = "a" * 64
        email = f"{local}@example.com"
        r = client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        assert r.status_code == 201

    def test_register_returns_different_user_ids(self, client: TestClient):
        ids = []
        for _ in range(3):
            r = client.post("/api/auth/register",
                            json={"email": _unique_email(), "password": "pass1234"})
            ids.append(r.json()["user_id"])
        assert len(set(ids)) == 3


# ── Login scenarios ───────────────────────────────────────────────────────────

class TestLoginScenarios:
    def test_login_with_leading_trailing_spaces_in_email(self, client: TestClient):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r = client.post("/api/auth/login",
                        json={"email": f"  {email}  ", "password": "pass1234"})
        assert r.status_code == 200

    def test_multiple_tokens_all_valid(self, client: TestClient):
        """Multiple login calls produce valid tokens that all grant access."""
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        tokens = []
        for _ in range(3):
            r = client.post("/api/auth/login",
                            json={"email": email, "password": "pass1234"})
            tokens.append(r.json()["access_token"])
        # All should grant access
        for t in tokens:
            r = client.get("/api/auth/me", headers=_headers(t))
            assert r.status_code == 200

    def test_token_still_works_after_password_change(self, client: TestClient):
        """Old token remains valid after password change because JWT is stateless
        and does not get revoked. This is expected behavior for this system."""
        email, _, token = _register_login(client)
        # Change password
        client.post("/api/auth/change-password",
                    json={"old_password": "pass1234", "new_password": "newpass789"},
                    headers=_headers(token))
        # Old token still works (JWT is stateless)
        r = client.get("/api/auth/me", headers=_headers(token))
        assert r.status_code == 200

    def test_login_response_contains_no_sensitive_fields(self, client: TestClient):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        user = r.json()["user"]
        for key in ("password_hash", "email_verify_token", "mfa_secret",
                     "mfa_secret_pending"):
            assert key not in user

    def test_login_with_mixed_case_email(self, client: TestClient):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        mixed = email[0].upper() + email[1:].upper()
        r = client.post("/api/auth/login", json={"email": mixed, "password": "pass1234"})
        assert r.status_code == 200


# ── Account deletion data cleanup ────────────────────────────────────────────

class TestAccountDeletionCleanup:
    def test_delete_account_removes_projects_and_protocols(self, client: TestClient):
        email, pw, token = _register_login(client)
        h = _headers(token)
        # Create project
        proj = client.post("/api/projects", json={"name": "ToDelete"}, headers=h)
        project_id = proj.json()["id"]
        # Create protocol
        proto = client.post("/api/user-protocols", json={
            "name": "ToDelete", "mode": "custom", "paradigm_ids": [],
            "duration_min": 5, "intensity": "low", "blocks": 1,
            "rest_duration_sec": 15, "practice_enabled": False,
        }, headers=h)
        protocol_id = proto.json()["id"]
        # Create field templates
        client.put("/api/user/field-templates",
                   json={"templates": ["Age", "Group"]}, headers=h)
        # Delete account
        client.request("DELETE", "/api/auth/account",
                       json={"password": pw}, headers=h)
        # Re-register same email to verify data is gone
        r = client.post("/api/auth/register",
                        json={"email": email, "password": "newpass123"})
        assert r.status_code == 201
        r2 = client.post("/api/auth/login",
                         json={"email": email, "password": "newpass123"})
        new_token = r2.json()["access_token"]
        h2 = _headers(new_token)
        # Projects should be empty
        projects = client.get("/api/projects", headers=h2).json()
        assert not any(p["id"] == project_id for p in projects)
        # Protocols should be empty
        protocols = client.get("/api/user-protocols", headers=h2).json()
        assert not any(p["id"] == protocol_id for p in protocols)
        # Field templates should be fresh/empty
        templates = client.get("/api/user/field-templates", headers=h2).json()
        assert templates["templates"] == []

    def test_delete_account_old_token_cannot_create_data(self, client: TestClient):
        _, pw, token = _register_login(client)
        h = _headers(token)
        client.request("DELETE", "/api/auth/account",
                       json={"password": pw}, headers=h)
        # Old token cannot create projects
        r = client.post("/api/projects", json={"name": "Ghost"}, headers=h)
        assert r.status_code == 401
        # Old token cannot access me
        r2 = client.get("/api/auth/me", headers=h)
        assert r2.status_code == 401

    def test_delete_account_sessions_kept_as_research_data(self, client: TestClient):
        """Session files are research data and should not be deleted with account."""
        email, pw, token = _register_login(client)
        uid = _get_user_id(client, token)
        h = _headers(token)
        filename = _make_session("kept_data", owner_id=uid)
        # Verify session exists
        r = client.get(f"/api/sessions/{filename}", headers=h)
        assert "trials" in r.json()
        # Delete account
        client.request("DELETE", "/api/auth/account",
                       json={"password": pw}, headers=h)
        # Session file should still exist on disk (research data preserved)
        session_path = os.path.join(_TMPDIR, filename)
        assert os.path.isfile(session_path)


# ── Session CRUD scenarios ────────────────────────────────────────────────────

class TestSessionCRUDScenarios:
    def test_create_multiple_delete_one_others_remain(self, client: TestClient):
        email, _, token = _register_login(client)
        uid = _get_user_id(client, token)
        h = _headers(token)
        f1 = _make_session("multi_a", owner_id=uid)
        f2 = _make_session("multi_b", owner_id=uid)
        f3 = _make_session("multi_c", owner_id=uid)
        # Delete f2
        client.request("DELETE", f"/api/sessions/{f2}", headers=h)
        # f1 and f3 remain
        fnames = [s["filename"] for s in client.get("/api/sessions", headers=h).json()]
        assert f1 in fnames
        assert f2 not in fnames
        assert f3 in fnames

    def test_session_notes_persist_across_reads(self, client: TestClient):
        email, _, token = _register_login(client)
        uid = _get_user_id(client, token)
        h = _headers(token)
        filename = _make_session("notes_persist", owner_id=uid)
        client.patch(f"/api/sessions/{filename}/notes",
                     json={"notes": "Important finding"}, headers=h)
        # Read twice to verify persistence
        for _ in range(2):
            data = client.get(f"/api/sessions/{filename}", headers=h).json()
            assert data.get("notes") == "Important finding"

    def test_session_notes_with_special_characters(self, client: TestClient):
        email, _, token = _register_login(client)
        uid = _get_user_id(client, token)
        h = _headers(token)
        filename = _make_session("special_notes", owner_id=uid)
        notes = 'Notes with "quotes", <tags>, &ampersands, and unicode: \u00e4\u00f6\u00fc'
        client.patch(f"/api/sessions/{filename}/notes",
                     json={"notes": notes}, headers=h)
        data = client.get(f"/api/sessions/{filename}", headers=h).json()
        assert data.get("notes") == notes

    def test_session_notes_overwrite(self, client: TestClient):
        email, _, token = _register_login(client)
        uid = _get_user_id(client, token)
        h = _headers(token)
        filename = _make_session("overwrite", owner_id=uid)
        client.patch(f"/api/sessions/{filename}/notes",
                     json={"notes": "First"}, headers=h)
        client.patch(f"/api/sessions/{filename}/notes",
                     json={"notes": "Second"}, headers=h)
        data = client.get(f"/api/sessions/{filename}", headers=h).json()
        assert data.get("notes") == "Second"

    def test_filter_sessions_by_participant_returns_only_matching(self, client: TestClient):
        email, _, token = _register_login(client)
        uid = _get_user_id(client, token)
        h = _headers(token)
        f1 = _make_session("participant_alpha", owner_id=uid)
        f2 = _make_session("participant_beta", owner_id=uid)
        # Filter for alpha
        result = client.get("/api/sessions?participant_id=participant_alpha", headers=h).json()
        fnames = [s["filename"] for s in result]
        assert f1 in fnames
        assert f2 not in fnames


# ── Project-session interaction scenarios ─────────────────────────────────────

class TestProjectSessionInteraction:
    def test_delete_session_while_attached_to_project(self, client: TestClient):
        """Deleting a session file should work even if it is attached to a project.
        The project should retain the filename reference (stale)."""
        email, _, token = _register_login(client)
        uid = _get_user_id(client, token)
        h = _headers(token)
        filename = _make_session("proj_attached", owner_id=uid)
        # Create project and attach
        proj = client.post("/api/projects", json={"name": "Attached"}, headers=h)
        pid = proj.json()["id"]
        client.post(f"/api/projects/{pid}/sessions",
                    json={"session_file": filename}, headers=h)
        # Delete the session file
        r = client.request("DELETE", f"/api/sessions/{filename}", headers=h)
        assert r.status_code == 200
        # Project still has the reference
        project = client.get(f"/api/projects/{pid}", headers=h).json()
        assert filename in project["session_files"]

    def test_project_with_many_sessions(self, client: TestClient):
        email, _, token = _register_login(client)
        uid = _get_user_id(client, token)
        h = _headers(token)
        proj = client.post("/api/projects", json={"name": "Many"}, headers=h)
        pid = proj.json()["id"]
        filenames = []
        for i in range(5):
            f = _make_session(f"many_{i}", owner_id=uid)
            filenames.append(f)
            client.post(f"/api/projects/{pid}/sessions",
                        json={"session_file": f}, headers=h)
        project = client.get(f"/api/projects/{pid}", headers=h).json()
        for f in filenames:
            assert f in project["session_files"]

    def test_detach_session_does_not_delete_it(self, client: TestClient):
        email, _, token = _register_login(client)
        uid = _get_user_id(client, token)
        h = _headers(token)
        filename = _make_session("detach_keep", owner_id=uid)
        proj = client.post("/api/projects", json={"name": "Detach"}, headers=h)
        pid = proj.json()["id"]
        client.post(f"/api/projects/{pid}/sessions",
                    json={"session_file": filename}, headers=h)
        # Detach
        client.request("DELETE", f"/api/projects/{pid}/sessions/{filename}", headers=h)
        # Session still accessible
        r = client.get(f"/api/sessions/{filename}", headers=h)
        assert "trials" in r.json()


# ── MFA lifecycle scenarios ───────────────────────────────────────────────────

class TestMFALifecycle:
    def test_disable_then_reenable_mfa(self, client: TestClient):
        import pyotp
        email, pw, token = _register_login(client)
        h = _headers(token)
        # Setup and enable MFA
        setup1 = client.post("/api/auth/mfa/setup", headers=h)
        secret1 = setup1.json()["secret"]
        code1 = pyotp.TOTP(secret1).now()
        client.post("/api/auth/mfa/enable", json={"code": code1}, headers=h)
        me = client.get("/api/auth/me", headers=h).json()
        assert me["mfa_enabled"] is True
        # Disable MFA
        client.delete("/api/auth/mfa/disable", headers=h)
        me2 = client.get("/api/auth/me", headers=h).json()
        assert me2["mfa_enabled"] is False
        # Login should not require MFA
        r = client.post("/api/auth/login", json={"email": email, "password": pw})
        assert "access_token" in r.json()
        assert r.json().get("mfa_required") is not True
        # Re-setup and re-enable with new secret
        setup2 = client.post("/api/auth/mfa/setup", headers=h)
        secret2 = setup2.json()["secret"]
        assert secret2 != secret1  # New secret each time
        code2 = pyotp.TOTP(secret2).now()
        client.post("/api/auth/mfa/enable", json={"code": code2}, headers=h)
        me3 = client.get("/api/auth/me", headers=h).json()
        assert me3["mfa_enabled"] is True

    def test_mfa_login_wrong_code_does_not_consume_token(self, client: TestClient):
        """A wrong MFA code should not invalidate the mfa_token; the user
        can retry with the correct code."""
        import pyotp
        email, pw, token = _register_login(client)
        h = _headers(token)
        setup = client.post("/api/auth/mfa/setup", headers=h)
        secret = setup.json()["secret"]
        code = pyotp.TOTP(secret).now()
        client.post("/api/auth/mfa/enable", json={"code": code}, headers=h)
        # Login -> MFA required
        login_r = client.post("/api/auth/login",
                              json={"email": email, "password": pw})
        mfa_token = login_r.json()["mfa_token"]
        # Wrong code
        r1 = client.post("/api/auth/mfa/verify",
                         json={"mfa_token": mfa_token, "code": "000000"})
        assert r1.status_code == 401
        # Correct code with same mfa_token should work
        correct_code = pyotp.TOTP(secret).now()
        r2 = client.post("/api/auth/mfa/verify",
                         json={"mfa_token": mfa_token, "code": correct_code})
        assert r2.status_code == 200
        assert "access_token" in r2.json()

    def test_mfa_setup_without_enable_does_not_require_mfa_on_login(self, client: TestClient):
        """Calling /mfa/setup without /mfa/enable should not change login behavior."""
        email, pw, token = _register_login(client)
        h = _headers(token)
        client.post("/api/auth/mfa/setup", headers=h)
        # Login should still return access_token directly
        r = client.post("/api/auth/login", json={"email": email, "password": pw})
        assert "access_token" in r.json()
        assert r.json().get("mfa_required") is not True


# ── Profile edge cases ────────────────────────────────────────────────────────

class TestProfileEdgeCases:
    def test_display_name_exactly_64_chars(self, client: TestClient):
        _, _, token = _register_login(client)
        h = _headers(token)
        name = "x" * 64
        r = client.patch("/api/auth/profile", json={"display_name": name}, headers=h)
        assert r.status_code == 200
        assert r.json()["display_name"] == name

    def test_display_name_65_chars_rejected(self, client: TestClient):
        _, _, token = _register_login(client)
        h = _headers(token)
        r = client.patch("/api/auth/profile",
                         json={"display_name": "x" * 65}, headers=h)
        assert r.status_code == 422

    def test_display_name_with_unicode(self, client: TestClient):
        _, _, token = _register_login(client)
        h = _headers(token)
        name = "Dr. M\u00fcller-Schmidt"
        r = client.patch("/api/auth/profile", json={"display_name": name}, headers=h)
        assert r.status_code == 200
        assert r.json()["display_name"] == name

    def test_display_name_with_html_stored_as_is(self, client: TestClient):
        """HTML in display_name is stored verbatim. The frontend is responsible
        for escaping on render (React does this by default)."""
        _, _, token = _register_login(client)
        h = _headers(token)
        name = '<script>alert("xss")</script>'
        r = client.patch("/api/auth/profile", json={"display_name": name}, headers=h)
        assert r.status_code == 200
        assert r.json()["display_name"] == name

    def test_display_name_empty_string_sets_null(self, client: TestClient):
        _, _, token = _register_login(client)
        h = _headers(token)
        client.patch("/api/auth/profile",
                     json={"display_name": "Something"}, headers=h)
        r = client.patch("/api/auth/profile",
                         json={"display_name": ""}, headers=h)
        assert r.status_code == 200
        assert r.json()["display_name"] is None

    def test_display_name_whitespace_only_sets_null(self, client: TestClient):
        _, _, token = _register_login(client)
        h = _headers(token)
        r = client.patch("/api/auth/profile",
                         json={"display_name": "   "}, headers=h)
        assert r.status_code == 200
        assert r.json()["display_name"] is None

    def test_update_phone_and_display_name_simultaneously(self, client: TestClient):
        _, _, token = _register_login(client)
        h = _headers(token)
        r = client.patch("/api/auth/profile",
                         json={"phone": "+15551234567", "display_name": "Jane"},
                         headers=h)
        assert r.status_code == 200
        body = r.json()
        assert body["phone"] == "+15551234567"
        assert body["display_name"] == "Jane"

    def test_me_returns_all_expected_public_fields(self, client: TestClient):
        _, _, token = _register_login(client)
        h = _headers(token)
        me = client.get("/api/auth/me", headers=h).json()
        for field in ("id", "email", "phone", "display_name",
                      "email_verified", "mfa_enabled", "created"):
            assert field in me, f"Missing field: {field}"
        # Sensitive fields must not appear
        for field in ("password_hash", "email_verify_token", "mfa_secret",
                      "mfa_secret_pending"):
            assert field not in me, f"Leaked sensitive field: {field}"


# ── Cross-user isolation (comprehensive) ─────────────────────────────────────

class TestCrossUserIsolationComprehensive:
    def test_user_b_cannot_list_user_a_projects(self, client: TestClient):
        _, _, token_a = _register_login(client)
        _, _, token_b = _register_login(client)
        client.post("/api/projects", json={"name": "A's Project"},
                    headers=_headers(token_a))
        projects_b = client.get("/api/projects", headers=_headers(token_b)).json()
        assert not any(p["name"] == "A's Project" for p in projects_b)

    def test_user_b_cannot_delete_user_a_project(self, client: TestClient):
        _, _, token_a = _register_login(client)
        _, _, token_b = _register_login(client)
        proj = client.post("/api/projects", json={"name": "Protected"},
                           headers=_headers(token_a))
        pid = proj.json()["id"]
        r = client.delete(f"/api/projects/{pid}", headers=_headers(token_b))
        assert r.status_code == 404
        # Still exists for A
        r2 = client.get(f"/api/projects/{pid}", headers=_headers(token_a))
        assert r2.status_code == 200

    def test_user_b_cannot_attach_session_to_user_a_project(self, client: TestClient):
        _, _, token_a = _register_login(client)
        uid_b = None
        _, _, token_b = _register_login(client)
        uid_b = _get_user_id(client, token_b)
        proj = client.post("/api/projects", json={"name": "A's"},
                           headers=_headers(token_a))
        pid = proj.json()["id"]
        fname = _make_session("b_session", owner_id=uid_b)
        r = client.post(f"/api/projects/{pid}/sessions",
                        json={"session_file": fname}, headers=_headers(token_b))
        assert r.status_code == 404

    def test_user_b_cannot_list_user_a_protocols(self, client: TestClient):
        _, _, token_a = _register_login(client)
        _, _, token_b = _register_login(client)
        proto_body = {
            "name": "A's Protocol", "mode": "custom", "paradigm_ids": [],
            "duration_min": 5, "intensity": "low", "blocks": 1,
            "rest_duration_sec": 15, "practice_enabled": False,
        }
        client.post("/api/user-protocols", json=proto_body,
                    headers=_headers(token_a))
        protos_b = client.get("/api/user-protocols",
                              headers=_headers(token_b)).json()
        assert not any(p["name"] == "A's Protocol" for p in protos_b)

    def test_user_b_cannot_read_user_a_field_templates(self, client: TestClient):
        _, _, token_a = _register_login(client)
        _, _, token_b = _register_login(client)
        client.put("/api/user/field-templates",
                   json={"templates": ["Secret Field"]},
                   headers=_headers(token_a))
        r = client.get("/api/user/field-templates",
                       headers=_headers(token_b))
        assert "Secret Field" not in r.json()["templates"]


# ── Project update edge cases ─────────────────────────────────────────────────

class TestProjectUpdateEdgeCases:
    def test_update_description_to_empty_string(self, client: TestClient):
        _, _, token = _register_login(client)
        h = _headers(token)
        proj = client.post("/api/projects",
                           json={"name": "Desc Test", "description": "Initial"},
                           headers=h)
        pid = proj.json()["id"]
        r = client.put(f"/api/projects/{pid}",
                       json={"description": ""}, headers=h)
        # Empty string should be accepted (cleared)
        assert r.status_code == 200

    def test_update_project_name_to_same_value(self, client: TestClient):
        _, _, token = _register_login(client)
        h = _headers(token)
        proj = client.post("/api/projects", json={"name": "Same"}, headers=h)
        pid = proj.json()["id"]
        r = client.put(f"/api/projects/{pid}", json={"name": "Same"}, headers=h)
        assert r.status_code == 200
        assert r.json()["name"] == "Same"

    def test_create_multiple_projects_same_name(self, client: TestClient):
        """Multiple projects with the same name should be allowed."""
        _, _, token = _register_login(client)
        h = _headers(token)
        r1 = client.post("/api/projects", json={"name": "Duplicate"}, headers=h)
        r2 = client.post("/api/projects", json={"name": "Duplicate"}, headers=h)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["id"] != r2.json()["id"]


# ── Email verification scenarios ──────────────────────────────────────────────

class TestEmailVerificationScenarios:
    def test_old_token_invalid_after_resend(self, client: TestClient):
        """After resending verification, old token should not work."""
        email = _unique_email()
        first_token = []
        second_token = []
        with patch("backend.app.send_verification_email",
                   side_effect=lambda e, t: first_token.append(t)):
            client.post("/api/auth/register",
                        json={"email": email, "password": "pass1234"})
        with patch("backend.app.send_verification_email",
                   side_effect=lambda e, t: second_token.append(t)):
            client.post("/api/auth/resend-verification", json={"email": email})
        # Old token should fail
        r1 = client.get(f"/api/auth/verify-email?token={first_token[0]}")
        assert r1.status_code == 400
        # New token should work
        r2 = client.get(f"/api/auth/verify-email?token={second_token[0]}")
        assert r2.status_code == 200

    def test_verification_status_reflected_in_login_response(self, client: TestClient):
        email = _unique_email()
        captured_token = []
        with patch("backend.app.send_verification_email",
                   side_effect=lambda e, t: captured_token.append(t)):
            client.post("/api/auth/register",
                        json={"email": email, "password": "pass1234"})
        # Before verification
        r1 = client.post("/api/auth/login",
                         json={"email": email, "password": "pass1234"})
        assert r1.json()["user"]["email_verified"] is False
        # Verify
        client.get(f"/api/auth/verify-email?token={captured_token[0]}")
        # After verification
        r2 = client.post("/api/auth/login",
                         json={"email": email, "password": "pass1234"})
        assert r2.json()["user"]["email_verified"] is True

    def test_verify_empty_token_rejected(self, client: TestClient):
        r = client.get("/api/auth/verify-email?token=")
        assert r.status_code == 400


# ── Change password scenarios ─────────────────────────────────────────────────

class TestChangePasswordScenarios:
    def test_change_password_then_login_with_new(self, client: TestClient):
        email, old_pw, token = _register_login(client)
        new_pw = "brandnewpass99"
        client.post("/api/auth/change-password",
                    json={"old_password": old_pw, "new_password": new_pw},
                    headers=_headers(token))
        # New password works
        r = client.post("/api/auth/login",
                        json={"email": email, "password": new_pw})
        assert r.status_code == 200
        # Old password does not
        r2 = client.post("/api/auth/login",
                         json={"email": email, "password": old_pw})
        assert r2.status_code == 401

    def test_change_password_multiple_times(self, client: TestClient):
        email, pw, token = _register_login(client)
        h = _headers(token)
        passwords = [pw, "second_pw_9", "third_pass_X", "final_pass_Z"]
        for i in range(1, len(passwords)):
            r = client.post("/api/auth/change-password",
                            json={"old_password": passwords[i-1],
                                  "new_password": passwords[i]},
                            headers=h)
            assert r.status_code == 200
        # Only the last password works
        r = client.post("/api/auth/login",
                        json={"email": email, "password": passwords[-1]})
        assert r.status_code == 200

    def test_change_password_to_special_chars(self, client: TestClient):
        email, pw, token = _register_login(client)
        new_pw = '!@#$%^&*()_+-=[]{}|;:\'",.<>?/'
        client.post("/api/auth/change-password",
                    json={"old_password": pw, "new_password": new_pw},
                    headers=_headers(token))
        r = client.post("/api/auth/login",
                        json={"email": email, "password": new_pw})
        assert r.status_code == 200


# ── Full lifecycle with data creation and deletion ────────────────────────────

class TestFullLifecycleWithData:
    def test_register_create_all_data_types_delete_all_then_delete_account(
        self, client: TestClient
    ):
        """Register, create sessions, projects, protocols, templates, notes.
        Delete each individual resource. Then delete account."""
        email, pw, token = _register_login(client)
        uid = _get_user_id(client, token)
        h = _headers(token)
        # Create session
        fname = _make_session("lifecycle", owner_id=uid)
        # Add notes
        client.patch(f"/api/sessions/{fname}/notes",
                     json={"notes": "Test note"}, headers=h)
        # Create project
        proj = client.post("/api/projects",
                           json={"name": "Study", "description": "Lifecycle test"},
                           headers=h)
        pid = proj.json()["id"]
        # Attach session to project
        client.post(f"/api/projects/{pid}/sessions",
                    json={"session_file": fname}, headers=h)
        # Create protocol
        proto = client.post("/api/user-protocols", json={
            "name": "MyProto", "mode": "custom", "paradigm_ids": ["nback"],
            "duration_min": 10, "intensity": "high", "blocks": 3,
            "rest_duration_sec": 30, "practice_enabled": True,
        }, headers=h)
        proto_id = proto.json()["id"]
        # Create field templates
        client.put("/api/user/field-templates",
                   json={"templates": ["Age", "Gender"]}, headers=h)
        # Verify everything exists
        assert len(client.get("/api/sessions", headers=h).json()) >= 1
        assert len(client.get("/api/projects", headers=h).json()) >= 1
        assert len(client.get("/api/user-protocols", headers=h).json()) >= 1
        assert len(client.get("/api/user/field-templates", headers=h).json()["templates"]) == 2
        # Delete protocol
        client.delete(f"/api/user-protocols/{proto_id}", headers=h)
        assert not any(
            p["id"] == proto_id
            for p in client.get("/api/user-protocols", headers=h).json()
        )
        # Detach session from project
        client.request("DELETE", f"/api/projects/{pid}/sessions/{fname}", headers=h)
        # Delete session
        client.request("DELETE", f"/api/sessions/{fname}", headers=h)
        # Delete project
        client.delete(f"/api/projects/{pid}", headers=h)
        assert client.get(f"/api/projects/{pid}", headers=h).status_code == 404
        # Clear field templates
        client.put("/api/user/field-templates",
                   json={"templates": []}, headers=h)
        # Delete account
        r = client.request("DELETE", "/api/auth/account",
                           json={"password": pw}, headers=h)
        assert r.json()["ok"] is True
        # Confirm login fails
        r2 = client.post("/api/auth/login",
                         json={"email": email, "password": pw})
        assert r2.status_code == 401
