"""JWT-based authentication, bcrypt password hashing, and TOTP MFA.

Required packages (see requirements.txt):
    python-jose[cryptography]
    bcrypt
    pyotp
    qrcode[pil]
"""
import base64
import io
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
from jose import jwt
import pyotp
import qrcode

from .logging_utils import DATA_DIR

logger = logging.getLogger(__name__)

# ── Secret key: read from env or persist a generated key ─────────────────────
_KEY_FILE = os.path.join(DATA_DIR, ".secret_key")


def _load_or_create_secret() -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.isfile(_KEY_FILE):
        with open(_KEY_FILE) as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(_KEY_FILE, "w") as f:
        f.write(key)
    logger.info("Generated new JWT secret key at %s", _KEY_FILE)
    return key


SECRET_KEY: str = os.environ.get("SECRET_KEY") or _load_or_create_secret()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# ── Password hashing ──────────────────────────────────────────────────────────
# bcrypt >= 4.0 enforces the 72-byte limit rather than silently truncating.
# We truncate explicitly so that the behavior is transparent and testable.
_BCRYPT_MAX = 72


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode()[:_BCRYPT_MAX], _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode()[:_BCRYPT_MAX], hashed.encode())
    except Exception:
        return False


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    payload = {
        **data,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Raises jose.JWTError on invalid / expired tokens."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ── TOTP MFA ──────────────────────────────────────────────────────────────────

def generate_totp_secret() -> str:
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, email: str, issuer: str = "StressLab") -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def totp_qr_png_b64(secret: str, email: str) -> str:
    """Return a base64-encoded PNG of the TOTP QR code for display in the browser."""
    uri = totp_provisioning_uri(secret, email)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def verify_totp(secret: str, code: str) -> bool:
    """Accepts one window before/after to tolerate small clock drift."""
    return pyotp.TOTP(secret).verify(code, valid_window=1)
