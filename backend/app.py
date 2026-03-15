import asyncio
import collections
import csv
import io
import json
import logging
import re
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
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
from .logging_utils import save_session, list_sessions, load_session, DATA_DIR
from .events import EventMarker
from .auth import (
    hash_password, verify_password, create_token, decode_token,
    generate_totp_secret, totp_qr_png_b64, verify_totp,
)
from .users import (
    create_user, get_user_by_email, get_user_by_id, update_user, user_public,
    consume_email_verify_token, delete_user,
)
from .projects import (
    list_projects, get_project, create_project, update_project,
    delete_project, add_session_to_project, remove_session_from_project,
)
from .user_protocols import (
    list_user_protocols, create_user_protocol, delete_user_protocol,
)
from .email import send_verification_email
from .db import init_db

logger = logging.getLogger(__name__)

event_marker = EventMarker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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

# Serve frontend if built (Next.js static export)
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "out")

# ── Auth helpers ──────────────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=False)

# Simple in-memory brute-force protection: track (ip, email) → [timestamps]
_login_attempts: dict[str, list[float]] = collections.defaultdict(list)
_MAX_ATTEMPTS = 10
_WINDOW_SEC = 300  # 5 minutes


def _check_rate_limit(key: str) -> None:
    now = time.time()
    bucket = _login_attempts[key]
    bucket[:] = [t for t in bucket if now - t < _WINDOW_SEC]
    if len(bucket) >= _MAX_ATTEMPTS:
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
        return get_user_by_id(payload["sub"])
    except JWTError:
        return None


def _require_user(user: dict | None = Depends(_get_optional_user)) -> dict:
    if user is None:
        # Open-access mode: return anonymous placeholder user
        return {"id": "anonymous", "email": "anonymous"}
    return user


# --- REST Endpoints ---

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
def list_sessions_endpoint(participant_id: str | None = None):
    return list_sessions(participant_id)


@app.get("/api/sessions/{filename}")
def get_session_endpoint(filename: str):
    # Validate filename to prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        return {"error": "invalid filename"}
    data = load_session(filename)
    if data is None:
        return {"error": "not found"}
    return data


@app.get("/api/sessions/{filename}/csv")
def export_session_csv(filename: str):
    if "/" in filename or "\\" in filename or ".." in filename:
        return {"error": "invalid filename"}
    data = load_session(filename)
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
def update_session_notes(filename: str, body: SessionNotesUpdate):
    if "/" in filename or "\\" in filename or ".." in filename:
        return {"error": "invalid filename"}
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(filepath):
        return {"error": "not found"}
    with open(filepath) as f:
        data = json.load(f)
    data["notes"] = body.notes
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
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


class LoginBody(BaseModel):
    email: str
    password: str


@app.post("/api/auth/login")
def login(body: LoginBody, request: Request):
    _check_rate_limit(f"login:{request.client.host}:{body.email.strip().lower()}")
    email = body.email.strip().lower()
    user = get_user_by_email(email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if user.get("mfa_enabled"):
        mfa_token = create_token({"sub": user["id"], "type": "mfa-pending"}, expires_minutes=10)
        return {"mfa_required": True, "mfa_token": mfa_token}
    token = create_token({"sub": user["id"], "type": "access"})
    return {"access_token": token, "user": user_public(user)}


class MFAVerifyBody(BaseModel):
    mfa_token: str
    code: str


@app.post("/api/auth/mfa/verify")
def mfa_verify(body: MFAVerifyBody):
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
    token = create_token({"sub": user["id"], "type": "access"})
    return {"access_token": token, "user": user_public(user)}


@app.get("/api/auth/me")
def get_me(user: dict = Depends(_require_user)):
    return user_public(user)


@app.post("/api/auth/mfa/setup")
def mfa_setup(user: dict = Depends(_require_user)):
    secret = generate_totp_secret()
    update_user(user["id"], mfa_secret_pending=secret)
    qr = totp_qr_png_b64(secret, user["email"])
    return {"secret": secret, "qr_png_b64": qr}


class MFAEnableBody(BaseModel):
    code: str


@app.post("/api/auth/mfa/enable")
def mfa_enable(body: MFAEnableBody, user: dict = Depends(_require_user)):
    secret = user.get("mfa_secret_pending")
    if not secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No pending MFA setup. Call /mfa/setup first.")
    if not verify_totp(secret, body.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid TOTP code")
    update_user(user["id"], mfa_enabled=True, mfa_secret=secret, mfa_secret_pending=None)
    return {"ok": True}


@app.delete("/api/auth/mfa/disable")
def mfa_disable(user: dict = Depends(_require_user)):
    update_user(user["id"], mfa_enabled=False, mfa_secret=None, mfa_secret_pending=None)
    return {"ok": True}


class DeleteAccountBody(BaseModel):
    password: str


@app.delete("/api/auth/account")
def delete_account(body: DeleteAccountBody, user: dict = Depends(_require_user)):
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
def get_field_templates(user: dict = Depends(_require_user)):
    return {"templates": user.get("field_templates", [])}


@app.put("/api/user/field-templates")
def set_field_templates(body: FieldTemplatesBody, user: dict = Depends(_require_user)):
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
def list_projects_endpoint(user: dict = Depends(_require_user)):
    return list_projects(user["id"])


@app.post("/api/projects", status_code=status.HTTP_201_CREATED)
def create_project_endpoint(body: ProjectCreate, user: dict = Depends(_require_user)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Project name required")
    return create_project(user["id"], name, body.description.strip())


@app.get("/api/projects/{project_id}")
def get_project_endpoint(project_id: str, user: dict = Depends(_require_user)):
    project = get_project(project_id)
    if not project or project["owner_id"] != user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


@app.put("/api/projects/{project_id}")
def update_project_endpoint(project_id: str, body: ProjectUpdate,
                             user: dict = Depends(_require_user)):
    project = get_project(project_id)
    if not project or project["owner_id"] != user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = update_project(project_id, **kwargs)
    return updated


@app.delete("/api/projects/{project_id}")
def delete_project_endpoint(project_id: str, user: dict = Depends(_require_user)):
    project = get_project(project_id)
    if not project or project["owner_id"] != user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    delete_project(project_id)
    return {"ok": True}


class SessionAttachBody(BaseModel):
    session_file: str


@app.post("/api/projects/{project_id}/sessions")
def attach_session(project_id: str, body: SessionAttachBody,
                   user: dict = Depends(_require_user)):
    project = get_project(project_id)
    if not project or project["owner_id"] != user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    filename = body.session_file
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid filename")
    return add_session_to_project(project_id, filename)


@app.delete("/api/projects/{project_id}/sessions/{filename}")
def detach_session(project_id: str, filename: str, user: dict = Depends(_require_user)):
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
def list_user_protocols_endpoint(user: dict = Depends(_require_user)):
    return list_user_protocols(user["id"])


@app.post("/api/user-protocols", status_code=status.HTTP_201_CREATED)
def create_user_protocol_endpoint(body: UserProtocolBody, user: dict = Depends(_require_user)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Protocol name required")
    config = body.model_dump(exclude={"name"})
    return create_user_protocol(user["id"], name, config)


@app.delete("/api/user-protocols/{protocol_id}")
def delete_user_protocol_endpoint(protocol_id: str, user: dict = Depends(_require_user)):
    ok = delete_user_protocol(user["id"], protocol_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Protocol not found")
    return {"ok": True}


# --- WebSocket Session ---

@app.websocket("/ws/session")
async def session_websocket(websocket: WebSocket):
    await websocket.accept()
    session: SessionManager | None = None

    try:
        while True:
            msg = await websocket.receive_json()
            msg_type = msg.get("type")

            if msg_type == "start_session":
                config_data = msg.get("config", {})
                config = SessionConfig(**config_data)
                session = SessionManager(config)
                session.start()
                event_marker.session_start(config.participant_id)
                event_marker.block_start(1)
                await websocket.send_json({
                    "type": "session_started",
                    "score": session.get_score(),
                })

            elif msg_type == "request_trial":
                if session is None:
                    await websocket.send_json({"type": "error", "message": "No active session"})
                    continue
                if session.is_time_up():
                    summary = session.get_summary()
                    filepath = save_session(summary)
                    add_session_file(session.config.participant_id, filepath)
                    event_marker.session_end(session.config.participant_id)
                    await websocket.send_json({
                        "type": "session_complete",
                        "data": summary.model_dump(),
                        "session_file": os.path.basename(filepath),
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
                    filepath = save_session(summary)
                    add_session_file(session.config.participant_id, filepath)
                    event_marker.session_end(session.config.participant_id)
                    await websocket.send_json({
                        "type": "session_complete",
                        "data": summary.model_dump(),
                        "session_file": os.path.basename(filepath),
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
                filepath = save_session(summary)
                add_session_file(session.config.participant_id, filepath)
                event_marker.session_end(session.config.participant_id)
                await websocket.send_json({
                    "type": "session_complete",
                    "data": summary.model_dump(),
                    "session_file": os.path.basename(filepath),
                })
                break

    except WebSocketDisconnect:
        if session and session.state.value not in ("complete", "idle"):
            summary = session.get_summary()
            save_session(summary)
            event_marker.session_end(session.config.participant_id)
        logger.info("WebSocket disconnected")


# Serve frontend: Next.js static export (out/ directory)
if os.path.isdir(FRONTEND_DIST):
    # Serve _next directory for built assets
    _next_dir = os.path.join(FRONTEND_DIST, "_next")
    if os.path.isdir(_next_dir):
        app.mount("/_next", StaticFiles(directory=_next_dir), name="next-assets")

    @app.get("/favicon.ico")
    async def favicon():
        path = os.path.join(FRONTEND_DIST, "favicon.ico")
        if os.path.isfile(path):
            return FileResponse(path)

    @app.get("/")
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
                     "/verify-email", "/projects", "/support", "/briefing"):
        _route_html = os.path.join(FRONTEND_DIST, f"{_prefix.lstrip('/')}.html")
        if not os.path.isfile(_route_html):
            _route_html = os.path.join(FRONTEND_DIST, "index.html")
        _handler_fn = _make_route_handler(_route_html)
        app.get(f"{_prefix}/{{rest:path}}", include_in_schema=False)(_handler_fn)
        app.get(f"{_prefix}", include_in_schema=False)(_handler_fn)
