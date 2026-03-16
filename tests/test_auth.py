"""
Comprehensive auth and account management tests.

Tests the full lifecycle: register -> verify email -> login -> change password
-> MFA setup/enable/verify/disable -> delete account, plus all error paths and
protected-route enforcement.

Storage: runs against the JSON file fallback (DATABASE_URL is unset in test
environment). Module-level path variables are redirected to a temp directory
before the FastAPI app is imported.
"""
import json
import os
import secrets
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ── Redirect file storage to an isolated temp directory before app import ────

_TMPDIR = tempfile.mkdtemp(prefix="stresslab_test_")

import backend.logging_utils as _lu  # noqa: E402
import backend.users as _um  # noqa: E402
import backend.participant as _pm  # noqa: E402
import backend.auth as _am  # noqa: E402
import backend.projects as _prm  # noqa: E402
import backend.user_protocols as _upm  # noqa: E402

_lu.DATA_DIR = _TMPDIR
_um.USERS_FILE = os.path.join(_TMPDIR, "users.json")
_pm.PARTICIPANTS_FILE = os.path.join(_TMPDIR, "participants.json")
_prm.PROJECTS_FILE = os.path.join(_TMPDIR, "projects.json")
_upm.PROTOCOLS_FILE = os.path.join(_TMPDIR, "protocols.json")
_am._KEY_FILE = os.path.join(_TMPDIR, ".secret_key")
_am.SECRET_KEY = _am._load_or_create_secret()  # regenerate against temp key file

from backend.app import app  # noqa: E402 — must come after path patching

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with patch("backend.app.send_verification_email", return_value=None):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Clear the in-memory rate-limit buckets before every test so that the
    large number of register/login calls across the suite does not trigger
    429s on unrelated tests. TestRateLimiting tests re-populate the bucket
    themselves within the same test body."""
    import backend.app as _app_mod
    _app_mod._login_attempts.clear()
    yield
    _app_mod._login_attempts.clear()


def _unique_email() -> str:
    return f"user_{secrets.token_hex(4)}@example.com"


# ── Registration ──────────────────────────────────────────────────────────────

class TestRegister:
    def test_success(self, client: TestClient):
        r = client.post("/api/auth/register", json={
            "email": _unique_email(), "password": "validpass123"
        })
        assert r.status_code == 201
        body = r.json()
        assert "user_id" in body

    def test_duplicate_email(self, client: TestClient):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r = client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        assert r.status_code == 409

    def test_email_case_insensitive_duplicate(self, client: TestClient):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r = client.post("/api/auth/register", json={
            "email": email.upper(), "password": "pass1234"
        })
        assert r.status_code == 409

    def test_invalid_email(self, client: TestClient):
        r = client.post("/api/auth/register", json={
            "email": "notanemail", "password": "pass1234"
        })
        assert r.status_code == 422

    def test_short_password(self, client: TestClient):
        r = client.post("/api/auth/register", json={
            "email": _unique_email(), "password": "short"
        })
        assert r.status_code == 422

    def test_sends_verification_email(self, client: TestClient):
        email = _unique_email()
        with patch("backend.app.send_verification_email") as mock_send:
            client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[0] == email
            assert len(args[1]) > 10  # token present

    def test_with_phone(self, client: TestClient):
        r = client.post("/api/auth/register", json={
            "email": _unique_email(), "password": "pass1234", "phone": "+15550001234"
        })
        assert r.status_code == 201


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    @pytest.fixture(scope="class")
    def registered(self, client):
        email = _unique_email()
        password = "logintest123"
        client.post("/api/auth/register", json={"email": email, "password": password})
        return email, password

    def test_success(self, client: TestClient, registered):
        email, password = registered
        r = client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "user" in body
        assert body["user"]["email"] == email

    def test_wrong_password(self, client: TestClient, registered):
        email, _ = registered
        r = client.post("/api/auth/login", json={"email": email, "password": "wrongpass"})
        assert r.status_code == 401

    def test_unknown_email(self, client: TestClient):
        r = client.post("/api/auth/login", json={
            "email": "nobody@example.com", "password": "pass1234"
        })
        assert r.status_code == 401

    def test_case_insensitive_email(self, client: TestClient, registered):
        email, password = registered
        r = client.post("/api/auth/login", json={
            "email": email.upper(), "password": password
        })
        assert r.status_code == 200


# ── Email verification ────────────────────────────────────────────────────────

class TestEmailVerification:
    def test_verify_valid_token(self, client: TestClient):
        email = _unique_email()
        captured_token: list[str] = []

        def capture_send(e, token):
            captured_token.append(token)

        with patch("backend.app.send_verification_email", side_effect=capture_send):
            client.post("/api/auth/register", json={"email": email, "password": "pass1234"})

        assert captured_token, "send_verification_email was not called"
        r = client.get(f"/api/auth/verify-email?token={captured_token[0]}")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_verify_invalid_token(self, client: TestClient):
        r = client.get("/api/auth/verify-email?token=totallywrongtoken")
        assert r.status_code == 400

    def test_verify_already_verified_token_fails(self, client: TestClient):
        email = _unique_email()
        captured_token: list[str] = []

        def capture_send(e, token):
            captured_token.append(token)

        with patch("backend.app.send_verification_email", side_effect=capture_send):
            client.post("/api/auth/register", json={"email": email, "password": "pass1234"})

        token = captured_token[0]
        client.get(f"/api/auth/verify-email?token={token}")  # first use
        r = client.get(f"/api/auth/verify-email?token={token}")  # second use
        assert r.status_code == 400

    def test_resend_returns_generic_message(self, client: TestClient):
        # Should not reveal whether email exists
        r = client.post("/api/auth/resend-verification",
                        json={"email": "nobody@example.com"})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_resend_updates_token(self, client: TestClient):
        email = _unique_email()
        first_token: list[str] = []
        second_token: list[str] = []

        with patch("backend.app.send_verification_email",
                   side_effect=lambda e, t: first_token.append(t)):
            client.post("/api/auth/register", json={"email": email, "password": "pass1234"})

        with patch("backend.app.send_verification_email",
                   side_effect=lambda e, t: second_token.append(t)):
            client.post("/api/auth/resend-verification", json={"email": email})

        assert first_token and second_token
        assert first_token[0] != second_token[0]
        # New token should work
        r = client.get(f"/api/auth/verify-email?token={second_token[0]}")
        assert r.status_code == 200


# ── Protected route enforcement ───────────────────────────────────────────────

class TestProtectedRoutes:
    PROTECTED = [
        ("GET", "/api/auth/me"),
        ("POST", "/api/auth/mfa/setup"),
        ("POST", "/api/auth/change-password"),
        ("DELETE", "/api/auth/account"),
        ("GET", "/api/projects"),
        ("POST", "/api/projects"),
        ("GET", "/api/user-protocols"),
        ("POST", "/api/user-protocols"),
        ("GET", "/api/user/field-templates"),
        ("PUT", "/api/user/field-templates"),
    ]

    def _login(self, client: TestClient) -> str:
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        return r.json()["access_token"]

    @pytest.mark.parametrize("method,path", PROTECTED)
    def test_requires_auth(self, client: TestClient, method: str, path: str):
        r = client.request(method, path, json={})
        assert r.status_code == 401, f"{method} {path} should return 401 without auth"

    def test_valid_token_grants_access_to_me(self, client: TestClient):
        token = self._login(client)
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert "email" in r.json()

    def test_tampered_token_is_rejected(self, client: TestClient):
        token = self._login(client)
        bad_token = token[:-5] + "XXXXX"
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
        assert r.status_code == 401

    def test_open_routes_work_without_auth(self, client: TestClient):
        """Paradigms, protocols, and participants do not require a token."""
        assert client.get("/api/paradigms").status_code == 200
        assert client.get("/api/protocols").status_code == 200
        assert client.get("/api/participants").status_code == 200


# ── Change password ───────────────────────────────────────────────────────────

class TestChangePassword:
    @pytest.fixture(scope="class")
    def authed(self, client):
        email = _unique_email()
        password = "original123"
        client.post("/api/auth/register", json={"email": email, "password": password})
        r = client.post("/api/auth/login", json={"email": email, "password": password})
        return email, password, r.json()["access_token"]

    def test_change_success(self, client: TestClient, authed):
        email, old_pw, token = authed
        r = client.post(
            "/api/auth/change-password",
            json={"old_password": old_pw, "new_password": "newpassword456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        # Old password no longer works
        r2 = client.post("/api/auth/login", json={"email": email, "password": old_pw})
        assert r2.status_code == 401
        # New password works
        r3 = client.post("/api/auth/login",
                         json={"email": email, "password": "newpassword456"})
        assert r3.status_code == 200

    def test_wrong_old_password(self, client: TestClient, authed):
        _, _, token = authed
        r = client.post(
            "/api/auth/change-password",
            json={"old_password": "wrongold", "new_password": "brandnew789"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 401

    def test_new_password_too_short(self, client: TestClient):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r_login = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        token = r_login.json()["access_token"]
        r = client.post(
            "/api/auth/change-password",
            json={"old_password": "pass1234", "new_password": "short"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422

    def test_new_password_too_long(self, client: TestClient):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r_login = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        token = r_login.json()["access_token"]
        r = client.post(
            "/api/auth/change-password",
            json={"old_password": "pass1234", "new_password": "x" * 73},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422


# ── Profile update ────────────────────────────────────────────────────────────

class TestProfile:
    def _authed(self, client: TestClient):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        return r.json()["access_token"]

    def test_update_phone(self, client: TestClient):
        token = self._authed(client)
        r = client.patch(
            "/api/auth/profile",
            json={"phone": "+15550009999"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["phone"] == "+15550009999"

    def test_clear_phone(self, client: TestClient):
        token = self._authed(client)
        client.patch("/api/auth/profile", json={"phone": "+15550001234"},
                     headers={"Authorization": f"Bearer {token}"})
        r = client.patch("/api/auth/profile", json={"phone": ""},
                         headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["phone"] is None

    def test_me_returns_email_verified(self, client: TestClient):
        token = self._authed(client)
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert "email_verified" in r.json()


# ── MFA ───────────────────────────────────────────────────────────────────────

class TestMFA:
    def _authed(self, client: TestClient):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        return email, "pass1234", r.json()["access_token"]

    def test_setup_returns_qr(self, client: TestClient):
        _, _, token = self._authed(client)
        r = client.post("/api/auth/mfa/setup",
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert "secret" in body
        assert "qr_png_b64" in body

    def test_enable_with_valid_code(self, client: TestClient):
        import pyotp
        _, _, token = self._authed(client)
        setup_r = client.post("/api/auth/mfa/setup",
                              headers={"Authorization": f"Bearer {token}"})
        secret = setup_r.json()["secret"]
        code = pyotp.TOTP(secret).now()
        r = client.post("/api/auth/mfa/enable", json={"code": code},
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_enable_with_invalid_code(self, client: TestClient):
        _, _, token = self._authed(client)
        client.post("/api/auth/mfa/setup", headers={"Authorization": f"Bearer {token}"})
        r = client.post("/api/auth/mfa/enable", json={"code": "000000"},
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_enable_without_setup_fails(self, client: TestClient):
        _, _, token = self._authed(client)
        # Enable without calling setup first
        r = client.post("/api/auth/mfa/enable", json={"code": "123456"},
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 400

    def test_login_requires_mfa_code_when_enabled(self, client: TestClient):
        import pyotp
        email, password, token = self._authed(client)
        setup_r = client.post("/api/auth/mfa/setup",
                              headers={"Authorization": f"Bearer {token}"})
        secret = setup_r.json()["secret"]
        code = pyotp.TOTP(secret).now()
        client.post("/api/auth/mfa/enable", json={"code": code},
                    headers={"Authorization": f"Bearer {token}"})

        # Login should now return mfa_required
        login_r = client.post("/api/auth/login",
                              json={"email": email, "password": password})
        assert login_r.status_code == 200
        body = login_r.json()
        assert body.get("mfa_required") is True
        mfa_token = body["mfa_token"]

        # Complete MFA login
        code2 = pyotp.TOTP(secret).now()
        verify_r = client.post("/api/auth/mfa/verify",
                               json={"mfa_token": mfa_token, "code": code2})
        assert verify_r.status_code == 200
        assert "access_token" in verify_r.json()

    def test_disable_mfa(self, client: TestClient):
        import pyotp
        _, _, token = self._authed(client)
        setup_r = client.post("/api/auth/mfa/setup",
                              headers={"Authorization": f"Bearer {token}"})
        secret = setup_r.json()["secret"]
        code = pyotp.TOTP(secret).now()
        client.post("/api/auth/mfa/enable", json={"code": code},
                    headers={"Authorization": f"Bearer {token}"})
        r = client.delete("/api/auth/mfa/disable",
                          headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        me = client.get("/api/auth/me",
                        headers={"Authorization": f"Bearer {token}"}).json()
        assert me["mfa_enabled"] is False


# ── Projects ──────────────────────────────────────────────────────────────────

class TestProjects:
    @pytest.fixture(scope="class")
    def authed(self, client):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_create_and_list(self, client: TestClient, authed):
        r = client.post("/api/projects",
                        json={"name": "Study A", "description": "Test study"},
                        headers=authed)
        assert r.status_code == 201
        pid = r.json()["id"]
        projects = client.get("/api/projects", headers=authed).json()
        assert any(p["id"] == pid for p in projects)

    def test_empty_name_rejected(self, client: TestClient, authed):
        r = client.post("/api/projects", json={"name": "   "}, headers=authed)
        assert r.status_code == 422

    def test_get_own_project(self, client: TestClient, authed):
        r = client.post("/api/projects", json={"name": "Proj B"}, headers=authed)
        pid = r.json()["id"]
        r2 = client.get(f"/api/projects/{pid}", headers=authed)
        assert r2.status_code == 200
        assert r2.json()["name"] == "Proj B"

    def test_cannot_access_other_users_project(self, client: TestClient):
        # Create two users
        h1 = {}
        h2 = {}
        for h in (h1, h2):
            email = _unique_email()
            client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
            r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
            h["Authorization"] = f"Bearer {r.json()['access_token']}"

        # User 1 creates a project
        proj = client.post("/api/projects", json={"name": "Private"}, headers=h1).json()
        # User 2 tries to access it
        r = client.get(f"/api/projects/{proj['id']}", headers=h2)
        assert r.status_code == 404

    def test_delete_project(self, client: TestClient, authed):
        r = client.post("/api/projects", json={"name": "To delete"}, headers=authed)
        pid = r.json()["id"]
        del_r = client.delete(f"/api/projects/{pid}", headers=authed)
        assert del_r.status_code == 200
        get_r = client.get(f"/api/projects/{pid}", headers=authed)
        assert get_r.status_code == 404


# ── User protocols ────────────────────────────────────────────────────────────

class TestUserProtocols:
    @pytest.fixture(scope="class")
    def authed(self, client):
        email = _unique_email()
        client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
        r = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_create_and_list(self, client: TestClient, authed):
        payload = {
            "name": "My Protocol",
            "mode": "custom",
            "paradigm_ids": ["nback"],
            "duration_min": 10,
            "intensity": "medium",
            "blocks": 2,
            "rest_duration_sec": 30,
            "practice_enabled": False,
        }
        r = client.post("/api/user-protocols", json=payload, headers=authed)
        assert r.status_code == 201
        pid = r.json()["id"]
        protocols = client.get("/api/user-protocols", headers=authed).json()
        assert any(p["id"] == pid for p in protocols)

    def test_delete_protocol(self, client: TestClient, authed):
        payload = {
            "name": "Temp",
            "mode": "custom",
            "paradigm_ids": [],
            "duration_min": 5,
            "intensity": "low",
            "blocks": 1,
            "rest_duration_sec": 15,
            "practice_enabled": False,
        }
        r = client.post("/api/user-protocols", json=payload, headers=authed)
        pid = r.json()["id"]
        del_r = client.delete(f"/api/user-protocols/{pid}", headers=authed)
        assert del_r.status_code == 200

    def test_delete_nonexistent_protocol(self, client: TestClient, authed):
        r = client.delete("/api/user-protocols/doesnotexist", headers=authed)
        assert r.status_code == 404


# ── Delete account ────────────────────────────────────────────────────────────

class TestDeleteAccount:
    def _register_and_login(self, client: TestClient):
        email = _unique_email()
        password = "deltest123"
        client.post("/api/auth/register", json={"email": email, "password": password})
        r = client.post("/api/auth/login", json={"email": email, "password": password})
        return email, password, r.json()["access_token"]

    def test_wrong_password_rejected(self, client: TestClient):
        _, _, token = self._register_and_login(client)
        r = client.request(
            "DELETE",
            "/api/auth/account",
            json={"password": "wrongpassword"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 401

    def test_delete_success(self, client: TestClient):
        email, password, token = self._register_and_login(client)
        r = client.request(
            "DELETE",
            "/api/auth/account",
            json={"password": password},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Account no longer exists — login should fail
        r2 = client.post("/api/auth/login",
                         json={"email": email, "password": password})
        assert r2.status_code == 401

    def test_delete_removes_projects(self, client: TestClient):
        email, password, token = self._register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}
        # Create a project
        proj_r = client.post("/api/projects", json={"name": "Gone"}, headers=headers)
        assert proj_r.status_code == 201
        # Delete account
        client.request("DELETE", "/api/auth/account",
                       json={"password": password}, headers=headers)
        # Confirm the account is gone
        r = client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 401


# ── Rate limiting ─────────────────────────────────────────────────────────────

class TestRateLimiting:
    def test_login_rate_limit(self, client: TestClient):
        """After 10 failed attempts from same IP, should get 429."""
        import backend.app as _app_module
        # Clear any existing buckets
        _app_module._login_attempts.clear()

        email = "ratelimit@example.com"
        responses = [
            client.post("/api/auth/login", json={"email": email, "password": "wrong"})
            for _ in range(11)
        ]
        status_codes = [r.status_code for r in responses]
        # First 10 should be 401 (wrong credentials), 11th should be 429
        assert 429 in status_codes, "Rate limit not triggered after 10 attempts"
