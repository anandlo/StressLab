import sys
print(f"[BOOT] Python {sys.version}, loading backend.app", flush=True)
import asyncio
import collections
import csv
import io
import json
import logging
import re
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from jose import JWTError
from pydantic import BaseModel
import os

from .models import SessionConfig, Intensity
from .session import SessionManager
from .paradigms import PARADIGM_REGISTRY
from .protocol import PROTOCOL_PRESETS, PROTOCOL_REGISTRY
from .participant import (
    create_participant, get_participant, list_participants, add_session_file,
    update_participant, delete_participant)
from .logging_utils import save_session, list_sessions, load_session, patch_session_notes, delete_session, DATA_DIR
from .events import EventMarker
from .auth import (
    hash_password, verify_password, create_token, decode_token,
    generate_totp_secret, totp_qr_png_b64, verify_totp,
)
from .users import (
    create_user, get_user_by_email, get_user_by_id, update_user, user_public,
    consume_email_verify_token, delete_user, get_user_by_reset_token,
)
from .projects import (
    list_projects, get_project, create_project, update_project,
    delete_project, add_session_to_project, remove_session_from_project,
)
from .user_protocols import (
    list_user_protocols, create_user_protocol, delete_user_protocol,
)
from .email import send_verification_email, send_password_reset_email
from .db import init_db, DatabaseUnavailable

logger = logging.getLogger(__name__)

event_marker = EventMarker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .db import DATABASE_URL, _connect_kwargs
    if DATABASE_URL:
        try:
            import urllib.parse as _up
            _p = _up.urlparse(DATABASE_URL)
            _masked = DATABASE_URL.replace(_p.password or "", "***") if _p.password else DATABASE_URL
            print(f"[STARTUP] DATABASE_URL (masked): {_masked}", flush=True)
            kw = _connect_kwargs()
            print(
                f"[STARTUP] DB host={kw['host']} port={kw['port']} "
                f"user={kw['user']} db={kw['dbname']} "
                f"pwlen={len(kw['password'])} ssl={kw['sslmode']}",
                flush=True,
            )
        except Exception as e:
            print(f"[STARTUP] DATABASE_URL set but could not parse: {e}", flush=True)
    else:
        print("[STARTUP] No DATABASE_URL — using local JSON storage", flush=True)
    try:
        init_db()
    except Exception as exc:
        print(f"[STARTUP] init_db failed: {exc}", flush=True)
    event_marker.connect()
    yield
    event_marker.close()


app = FastAPI(title="Cognitive Stress Induction Tool", lifespan=lifespan)

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DatabaseUnavailable)
async def _db_unavailable(_request: Request, exc: DatabaseUnavailable):
    logger.error("Database unavailable: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unavailable. Please try again later."},
    )


# Serve frontend if built (Next.js static export)
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "out")

# ── Auth helpers ──────────────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=False)

# Simple in-memory brute-force protection: track (ip, email) → [timestamps]
_login_attempts: dict[str, list[float]] = collections.defaultdict(list)
_MAX_ATTEMPTS = 10
_WINDOW_SEC = 300  # 5 minutes


def _check_rate_limit(key: str, max_attempts: int = _MAX_ATTEMPTS) -> None:
    now = time.time()
    bucket = _login_attempts[key]
    bucket[:] = [t for t in bucket if now - t < _WINDOW_SEC]
    if len(bucket) >= max_attempts:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many attempts. Try again in 5 minutes.")
    bucket.append(now)


def _get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            return None
        user = get_user_by_id(payload["sub"])
        if user is None:
            return None
        # token_version mismatch means the token was invalidated (logout / password change)
        if payload.get("tv", 0) != (user.get("token_version") or 0):
            return None
        return user
    except JWTError:
        return None


def _require_user(user: dict | None = Depends(_get_optional_user)) -> dict:
    if user is None:
        # Open-access mode: return anonymous placeholder user
        return {"id": "anonymous", "email": "anonymous"}
    return user


def _require_auth(user: dict | None = Depends(_get_optional_user)) -> dict:
    """Hard 401 for routes that require a real account (projects, protocols, settings)."""
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    return user


# --- REST Endpoints ---

@app.get("/api/health")
def health_check():
    """Lightweight liveness probe used by keep-alive pings."""
    return {"ok": True}


@app.get("/api/paradigms")
def get_paradigms():
    return [p.meta.model_dump() for p in PARADIGM_REGISTRY.values()]


@app.get("/api/protocols")
def get_protocols():
    return [p.model_dump() for p in PROTOCOL_PRESETS]


class ParticipantCreate(BaseModel):
    id: str
    demographics: dict = {}


@app.post("/api/participants")
def create_participant_endpoint(body: ParticipantCreate):
    p = create_participant(body.id, body.demographics)
    return p.model_dump()


@app.get("/api/participants")
def list_participants_endpoint():
    return [p.model_dump() for p in list_participants()]


@app.get("/api/participants/{pid}")
def get_participant_endpoint(pid: str):
    p = get_participant(pid)
    if p is None:
        return {"error": "not found"}
    return p.model_dump()


class ParticipantUpdate(BaseModel):
    demographics: dict = {}


@app.put("/api/participants/{pid}")
def update_participant_endpoint(pid: str, body: ParticipantUpdate):
    p = update_participant(pid, body.demographics)
    if p is None:
        return {"error": "not found"}
    return p.model_dump()


@app.delete("/api/participants/{pid}")
def delete_participant_endpoint(pid: str):
    ok = delete_participant(pid)
    return {"ok": ok}


class PracticeRequest(BaseModel):
    paradigm_ids: list[str]


@app.post("/api/practice-trials")
def generate_practice_trials(body: PracticeRequest):
    config = SessionConfig(
        participant_id="practice",
        paradigm_ids=body.paradigm_ids,
        practice_trials_per_paradigm=1,
    )
    mgr = SessionManager(config)
    trials = mgr.generate_practice_trials()
    return [t.model_dump() for t in trials]


@app.get("/api/sessions")
def list_sessions_endpoint(
    participant_id: str | None = None,
    user: dict = Depends(_require_auth),
):
    return list_sessions(participant_id, owner_id=user["id"])


@app.get("/api/sessions/{filename}")
def get_session_endpoint(filename: str, user: dict = Depends(_require_auth)):
    if "/" in filename or "\\" in filename or ".." in filename:
        return {"error": "invalid filename"}
    data = load_session(filename, owner_id=user["id"])
    if data is None:
        return {"error": "not found"}
    return data


@app.get("/api/sessions/{filename}/csv")
def export_session_csv(filename: str, user: dict = Depends(_require_auth)):
    if "/" in filename or "\\" in filename or ".." in filename:
        return {"error": "invalid filename"}
    data = load_session(filename, owner_id=user["id"])
    if data is None:
        return {"error": "not found"}
    trials = data.get("trials", [])
    output = io.StringIO()
    writer = csv.writer(output)
    cols = ["trial_id", "paradigm_id", "paradigm_label", "difficulty",
            "correct_answer", "user_response", "is_correct", "timed_out",
            "response_time_ms"]
    writer.writerow(cols)
    for t in trials:
        writer.writerow([t.get(c, "") for c in cols])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename.replace(".json", ".csv")}"'},
    )


class SessionNotesUpdate(BaseModel):
    notes: str = ""


@app.patch("/api/sessions/{filename}/notes")
def update_session_notes(
    filename: str,
    body: SessionNotesUpdate,
    user: dict = Depends(_require_auth),
):
    if "/" in filename or "\\" in filename or ".." in filename:
        return {"error": "invalid filename"}
    ok = patch_session_notes(filename, body.notes, owner_id=user["id"])
    return {"ok": True} if ok else {"error": "not found"}


@app.delete("/api/sessions/{filename}")
def delete_session_endpoint(filename: str, user: dict = Depends(_require_auth)):
    """Permanently delete a stored session file. Requires authentication."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid filename")
    ok = delete_session(filename, owner_id=user["id"])
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return {"ok": True}


# --- Auth routes ---

class RegisterBody(BaseModel):
    email: str
    password: str
    phone: str | None = None


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterBody, request: Request):
    _check_rate_limit(f"register:{request.client.host}")
    email = body.email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid email address")
    if len(body.password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Password must be at least 8 characters")
    if get_user_by_email(email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    password_hash = hash_password(body.password)
    user = create_user(email, password_hash, phone=body.phone)
    send_verification_email(email, user["email_verify_token"])
    return {"message": "Account created. Check server logs for verification link (dev mode).",
            "user_id": user["id"]}


@app.get("/api/auth/verify-email")
def verify_email(token: str):
    if not token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing token")
    if consume_email_verify_token(token):
        return {"ok": True, "message": "Email verified successfully"}
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired token")


class ResendVerificationBody(BaseModel):
    email: str


@app.post("/api/auth/resend-verification")
def resend_verification(body: ResendVerificationBody, request: Request):
    _check_rate_limit(f"resend:{request.client.host}")
    email = body.email.strip().lower()
    # Always return the same generic message to prevent email enumeration
    generic = "If that address is registered and unverified, a verification link has been sent"
    user = get_user_by_email(email)
    if not user or user.get("email_verified"):
        return {"ok": True, "message": generic}
    new_token = secrets.token_urlsafe(32)
    new_expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    update_user(user["id"], email_verify_token=new_token, email_verify_token_expires=new_expires)
    send_verification_email(email, new_token)
    return {"ok": True, "message": generic}


class ChangePasswordBody(BaseModel):
    old_password: str
    new_password: str


@app.post("/api/auth/change-password")
def change_password(body: ChangePasswordBody, user: dict = Depends(_require_auth)):
    if not verify_password(body.old_password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect current password")
    if len(body.new_password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Password must be at least 8 characters")
    if len(body.new_password) > 72:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Password too long (max 72 characters)")
    new_version = (user.get("token_version") or 0) + 1
    update_user(user["id"], password_hash=hash_password(body.new_password), token_version=new_version)
    # Return a fresh token so the current session remains valid after the version bump
    new_token = create_token({"sub": user["id"], "type": "access", "tv": new_version})
    return {"ok": True, "access_token": new_token}


class ForgotPasswordBody(BaseModel):
    email: str


@app.post("/api/auth/forgot-password")
def forgot_password(body: ForgotPasswordBody, request: Request):
    _check_rate_limit(f"forgot:{request.client.host}")
    email = body.email.strip().lower()
    # Always return the same generic message to prevent email enumeration
    generic = "If that address is registered, a password reset link has been sent."
    user = get_user_by_email(email)
    if not user:
        return {"ok": True, "message": generic}
    reset_token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    update_user(user["id"], password_reset_token=reset_token, password_reset_expires=expires)
    send_password_reset_email(email, reset_token)
    return {"ok": True, "message": generic}


class ResetPasswordBody(BaseModel):
    token: str
    new_password: str


@app.post("/api/auth/reset-password")
def reset_password(body: ResetPasswordBody, request: Request):
    _check_rate_limit(f"reset:{request.client.host}")
    if len(body.new_password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Password must be at least 8 characters")
    if len(body.new_password) > 72:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Password too long (max 72 characters)")
    user = get_user_by_reset_token(body.token)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset link")
    new_version = (user.get("token_version") or 0) + 1
    update_user(
        user["id"],
        password_hash=hash_password(body.new_password),
        password_reset_token=None,
        password_reset_expires=None,
        token_version=new_version,
        lockout_until=None,
        failed_login_attempts=0,
    )
    return {"ok": True, "message": "Password has been reset. You can now sign in."}


@app.post("/api/auth/refresh")
def refresh_token(user: dict = Depends(_require_auth)):
    """Issue a fresh access token for an already-authenticated user."""
    token_version = user.get("token_version") or 0
    new_token = create_token({"sub": user["id"], "type": "access", "tv": token_version})
    return {"access_token": new_token, "user": user_public(user)}


@app.post("/api/auth/logout")
def logout(user: dict = Depends(_require_auth)):
    """Invalidate all existing sessions by incrementing token_version."""
    new_version = (user.get("token_version") or 0) + 1
    update_user(user["id"], token_version=new_version)
    return {"ok": True}


class LoginBody(BaseModel):
    email: str
    password: str


@app.post("/api/auth/login")
def login(body: LoginBody, request: Request):
    _check_rate_limit(f"login:{request.client.host}:{body.email.strip().lower()}")
    email = body.email.strip().lower()
    user = get_user_by_email(email)
    if not user or not verify_password(body.password, user["password_hash"]):
        # Increment failed attempts on valid-email wrong-password (but avoid enumeration
        # by only updating when user actually exists)
        if user:
            attempts = (user.get("failed_login_attempts") or 0) + 1
            updates: dict = {"failed_login_attempts": attempts}
            if attempts >= 5:
                lockout_until = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
                updates["lockout_until"] = lockout_until
            update_user(user["id"], **updates)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    # Check per-user lockout
    lockout_until = user.get("lockout_until")
    if lockout_until:
        if datetime.fromisoformat(lockout_until) > datetime.now(timezone.utc):
            raise HTTPException(status.HTTP_423_LOCKED,
                                "Account temporarily locked due to too many failed attempts. "
                                "Try again in 15 minutes.")
        # Lockout expired — clear it
        update_user(user["id"], lockout_until=None, failed_login_attempts=0)
    # Block unverified accounts
    if not user.get("email_verified"):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Email address not verified. Check your inbox for the verification link.")
    # Clear failed attempts on successful credential check
    if user.get("failed_login_attempts"):
        update_user(user["id"], failed_login_attempts=0)
    if user.get("mfa_enabled"):
        mfa_token = create_token({"sub": user["id"], "type": "mfa-pending"}, expires_minutes=10)
        return {"mfa_required": True, "mfa_token": mfa_token}
    token_version = user.get("token_version") or 0
    token = create_token({"sub": user["id"], "type": "access", "tv": token_version})
    return {"access_token": token, "user": user_public(user)}


class MFAVerifyBody(BaseModel):
    mfa_token: str
    code: str


@app.post("/api/auth/mfa/verify")
def mfa_verify(body: MFAVerifyBody, request: Request):
    _check_rate_limit(f"mfa:{request.client.host}", max_attempts=5)
    try:
        payload = decode_token(body.mfa_token)
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired MFA token")
    if payload.get("type") != "mfa-pending":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    if not verify_totp(user["mfa_secret"], body.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid TOTP code")
    token_version = user.get("token_version") or 0
    token = create_token({"sub": user["id"], "type": "access", "tv": token_version})
    return {"access_token": token, "user": user_public(user)}


@app.get("/api/auth/me")
def get_me(user: dict = Depends(_require_auth)):
    return user_public(user)


class UpdateProfileBody(BaseModel):
    phone: str | None = None
    display_name: str | None = None


@app.patch("/api/auth/profile")
def update_profile(body: UpdateProfileBody, user: dict = Depends(_require_auth)):
    updates: dict = {}
    if body.phone is not None:
        updates["phone"] = body.phone.strip() or None
    if "display_name" in body.model_fields_set:
        if body.display_name is None:
            updates["display_name"] = None
        else:
            name = body.display_name.strip()
            if len(name) > 64:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    "Display name must be 64 characters or fewer")
            updates["display_name"] = name or None
    if updates:
        update_user(user["id"], **updates)
    return user_public(get_user_by_id(user["id"]))


@app.post("/api/auth/mfa/setup")
def mfa_setup(user: dict = Depends(_require_auth)):
    secret = generate_totp_secret()
    update_user(user["id"], mfa_secret_pending=secret)
    qr = totp_qr_png_b64(secret, user["email"])
    return {"secret": secret, "qr_png_b64": qr}


class MFAEnableBody(BaseModel):
    code: str


@app.post("/api/auth/mfa/enable")
def mfa_enable(body: MFAEnableBody, user: dict = Depends(_require_auth)):
    secret = user.get("mfa_secret_pending")
    if not secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No pending MFA setup. Call /mfa/setup first.")
    if not verify_totp(secret, body.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid TOTP code")
    update_user(user["id"], mfa_enabled=True, mfa_secret=secret, mfa_secret_pending=None)
    return {"ok": True}


@app.delete("/api/auth/mfa/disable")
def mfa_disable(user: dict = Depends(_require_auth)):
    update_user(user["id"], mfa_enabled=False, mfa_secret=None, mfa_secret_pending=None)
    return {"ok": True}


class DeleteAccountBody(BaseModel):
    password: str


@app.delete("/api/auth/account")
def delete_account(body: DeleteAccountBody, user: dict = Depends(_require_auth)):
    """Permanently delete the authenticated user's account and all owned data.
    Requires current password for confirmation. Session records are kept."""
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect password")
    ok = delete_user(user["id"])
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return {"ok": True, "message": "Account and all owned data deleted."}


# --- User field-template routes ---
# Field templates are named custom demographic fields saved per user account.
# They appear pre-populated every time the user opens the "Add Participant" form.

class FieldTemplatesBody(BaseModel):
    templates: list[str]


@app.get("/api/user/field-templates")
def get_field_templates(user: dict = Depends(_require_auth)):
    return {"templates": user.get("field_templates", [])}


@app.put("/api/user/field-templates")
def set_field_templates(body: FieldTemplatesBody, user: dict = Depends(_require_auth)):
    # Deduplicate while preserving order; strip blanks
    seen: set[str] = set()
    cleaned: list[str] = []
    for name in body.templates:
        key = name.strip()
        if key and key not in seen:
            seen.add(key)
            cleaned.append(key)
    update_user(user["id"], field_templates=cleaned)
    return {"templates": cleaned}


# --- Project routes ---

class ProjectCreate(BaseModel):
    name: str
    description: str = ""


@app.get("/api/projects")
def list_projects_endpoint(user: dict = Depends(_require_auth)):
    return list_projects(user["id"])


@app.post("/api/projects", status_code=status.HTTP_201_CREATED)
def create_project_endpoint(body: ProjectCreate, user: dict = Depends(_require_auth)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Project name required")
    return create_project(user["id"], name, body.description.strip())


@app.get("/api/projects/{project_id}")
def get_project_endpoint(project_id: str, user: dict = Depends(_require_auth)):
    project = get_project(project_id)
    if not project or project["owner_id"] != user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


@app.put("/api/projects/{project_id}")
def update_project_endpoint(project_id: str, body: ProjectUpdate,
                             user: dict = Depends(_require_auth)):
    project = get_project(project_id)
    if not project or project["owner_id"] != user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = update_project(project_id, **kwargs)
    return updated


@app.delete("/api/projects/{project_id}")
def delete_project_endpoint(project_id: str, user: dict = Depends(_require_auth)):
    project = get_project(project_id)
    if not project or project["owner_id"] != user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    delete_project(project_id)
    return {"ok": True}


class SessionAttachBody(BaseModel):
    session_file: str


@app.post("/api/projects/{project_id}/sessions")
def attach_session(project_id: str, body: SessionAttachBody,
                   user: dict = Depends(_require_auth)):
    project = get_project(project_id)
    if not project or project["owner_id"] != user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    filename = body.session_file
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid filename")
    return add_session_to_project(project_id, filename)


@app.delete("/api/projects/{project_id}/sessions/{filename}")
def detach_session(project_id: str, filename: str, user: dict = Depends(_require_auth)):
    project = get_project(project_id)
    if not project or project["owner_id"] != user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return remove_session_from_project(project_id, filename)


# --- User protocol routes ---

class UserProtocolBody(BaseModel):
    name: str
    mode: str = "custom"
    preset_id: str | None = None
    paradigm_ids: list[str] = []
    duration_min: float = 10
    intensity: str = "medium"
    blocks: int = 2
    rest_duration_sec: int = 30
    practice_enabled: bool = False


@app.get("/api/user-protocols")
def list_user_protocols_endpoint(user: dict = Depends(_require_auth)):
    return list_user_protocols(user["id"])


@app.post("/api/user-protocols", status_code=status.HTTP_201_CREATED)
def create_user_protocol_endpoint(body: UserProtocolBody, user: dict = Depends(_require_auth)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Protocol name required")
    config = body.model_dump(exclude={"name"})
    return create_user_protocol(user["id"], name, config)


@app.delete("/api/user-protocols/{protocol_id}")
def delete_user_protocol_endpoint(protocol_id: str, user: dict = Depends(_require_auth)):
    ok = delete_user_protocol(user["id"], protocol_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Protocol not found")
    return {"ok": True}


# --- WebSocket Session ---

@app.websocket("/ws/session")
async def session_websocket(websocket: WebSocket):
    await websocket.accept()
    session: SessionManager | None = None
    # When a valid JWT is supplied in start_session, results are saved server-side.
    # Without a token the session runs fully in-memory; the full summary is sent
    # back to the client so the browser can persist it locally.
    save_to_server: bool = False
    owner_id: str | None = None

    def _maybe_save(s: SessionManager) -> str | None:
        """Save session server-side when authenticated. Returns basename or None."""
        if not save_to_server:
            return None
        summ = s.get_summary()
        custom_name = s.config.session_name or None
        filepath = save_session(summ, owner_id, session_name=custom_name)
        fname = os.path.basename(filepath)
        add_session_file(s.config.participant_id, filepath)
        # Auto-attach to project if requested
        if s.config.project_id:
            try:
                add_session_to_project(s.config.project_id, fname)
            except Exception:
                pass  # Non-critical: session is saved but project link failed
        return fname

    try:
        while True:
            msg = await websocket.receive_json()
            msg_type = msg.get("type")

            if msg_type == "start_session":
                # Validate optional auth token to decide persistence mode
                token_str = msg.get("auth_token")
                if token_str:
                    try:
                        payload = decode_token(token_str)
                        save_to_server = payload.get("type") == "access"
                        owner_id = payload.get("sub") if save_to_server else None
                    except Exception:
                        save_to_server = False
                        owner_id = None
                else:
                    save_to_server = False
                    owner_id = None

                config_data = msg.get("config", {})
                config = SessionConfig(**config_data)
                session = SessionManager(config)
                session.start()
                event_marker.session_start(config.participant_id)
                event_marker.block_start(1)
                await websocket.send_json({
                    "type": "session_started",
                    "score": session.get_score(),
                    "guest": not save_to_server,
                })

            elif msg_type == "request_trial":
                if session is None:
                    await websocket.send_json({"type": "error", "message": "No active session"})
                    continue
                if session.is_time_up():
                    summary = session.get_summary()
                    session_file = _maybe_save(session)
                    event_marker.session_end(session.config.participant_id)
                    await websocket.send_json({
                        "type": "session_complete",
                        "data": summary.model_dump(),
                        "session_file": session_file,
                        "guest": not save_to_server,
                    })
                    continue
                if session.should_rest():
                    event_marker.block_end(session.current_block + 1)
                    session.begin_rest()
                    await websocket.send_json({
                        "type": "rest",
                        "data": {
                            "duration_sec": session.config.rest_duration_sec,
                            "block_completed": session.current_block + 1,
                            "total_blocks": session.config.blocks,
                        },
                    })
                    continue
                trial = session.next_trial()
                if trial is None:
                    summary = session.get_summary()
                    session_file = _maybe_save(session)
                    event_marker.session_end(session.config.participant_id)
                    await websocket.send_json({
                        "type": "session_complete",
                        "data": summary.model_dump(),
                        "session_file": session_file,
                        "guest": not save_to_server,
                    })
                else:
                    event_marker.trial_start(
                        trial.trial_id, trial.paradigm_id, trial.difficulty)
                    await websocket.send_json({
                        "type": "trial",
                        "data": trial.model_dump(),
                    })

            elif msg_type == "submit_response":
                if session is None:
                    continue
                result = session.submit_answer(
                    trial_id=msg["trial_id"],
                    response=msg.get("response"),
                    response_time_ms=msg.get("response_time_ms", 0),
                    timed_out=msg.get("timed_out", False),
                )
                event_marker.trial_end(
                    result.trial_id, result.is_correct, result.response_time_ms)
                feedback = session.get_feedback()
                await websocket.send_json({
                    "type": "result",
                    "data": {
                        "correct": result.is_correct,
                        "correct_answer": result.correct_answer,
                        "user_response": result.user_response,
                        "timed_out": result.timed_out,
                        "response_time_ms": result.response_time_ms,
                        "score": session.get_score(),
                        "feedback": feedback,
                    },
                })

            elif msg_type == "rest_complete":
                if session is None:
                    continue
                session.end_rest()
                event_marker.block_start(session.current_block + 1)
                await websocket.send_json({
                    "type": "rest_ended",
                    "score": session.get_score(),
                })

            elif msg_type == "stop_session":
                if session is None:
                    continue
                summary = session.get_summary()
                session_file = _maybe_save(session)
                event_marker.session_end(session.config.participant_id)
                await websocket.send_json({
                    "type": "session_complete",
                    "data": summary.model_dump(),
                    "session_file": session_file,
                    "guest": not save_to_server,
                })
                break

            elif msg_type == "discard_session":
                if session is not None:
                    event_marker.session_end(session.config.participant_id)
                await websocket.send_json({"type": "session_discarded"})
                break

    except WebSocketDisconnect:
        if session and session.state.value not in ("complete", "idle"):
            if save_to_server:
                summary = session.get_summary()
                save_session(summary, owner_id)
            event_marker.session_end(session.config.participant_id)
        logger.info("WebSocket disconnected")


# Serve frontend: Next.js static export (out/ directory)
if os.path.isdir(FRONTEND_DIST):
    # Serve _next directory for built assets
    _next_dir = os.path.join(FRONTEND_DIST, "_next")
    if os.path.isdir(_next_dir):
        app.mount("/_next", StaticFiles(directory=_next_dir), name="next-assets")

    @app.api_route("/favicon.ico", methods=["GET", "HEAD"])
    async def favicon():
        path = os.path.join(FRONTEND_DIST, "favicon.ico")
        if os.path.isfile(path):
            return FileResponse(path)

    @app.api_route("/", methods=["GET", "HEAD"])
    async def root():
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

    # Serve each route's pre-rendered HTML from the static export
    def _make_route_handler(html_path: str):
        async def _handler(rest: str = ""):
            return FileResponse(html_path)
        return _handler

    for _prefix in ("/participants", "/protocol", "/practice",
                     "/session", "/results", "/library",
                     "/login", "/register", "/mfa-verify", "/mfa-setup",
                     "/verify-email", "/projects", "/support", "/briefing",
                     "/account", "/forgot-password", "/reset-password"):
        _route_html = os.path.join(FRONTEND_DIST, f"{_prefix.lstrip('/')}.html")
        if not os.path.isfile(_route_html):
            _route_html = os.path.join(FRONTEND_DIST, "index.html")
        _handler_fn = _make_route_handler(_route_html)
        app.api_route(f"{_prefix}/{{rest:path}}", methods=["GET", "HEAD"], include_in_schema=False)(_handler_fn)
        app.api_route(f"{_prefix}", methods=["GET", "HEAD"], include_in_schema=False)(_handler_fn)
