from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt

_ALGORITHM = "HS256"
# 1h : compromis entre securite et confort. Le refresh token (cookie httpOnly,
# 30j) prend le relais via /auth/refresh pour prolonger la session sans
# reconnexion.
_ACCESS_TOKEN_EXPIRE_MINUTES = 60
_REFRESH_TOKEN_EXPIRE_DAYS = 30


def _secret_key() -> str:
    key = os.getenv("DASHMONEY_SECRET_KEY", "").strip()
    if not key:
        raise RuntimeError("DASHMONEY_SECRET_KEY env var is required")
    return key


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "email": email, "exp": expire, "jti": str(uuid4())}
    return jwt.encode(payload, _secret_key(), algorithm=_ALGORITHM)


def create_refresh_token() -> str:
    """Generate a cryptographically secure opaque token (not a JWT)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hash of a token for safe storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_token_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT. Raises jwt.InvalidTokenError on failure.
    Returns the payload dict on success.
    """
    return jwt.decode(token, _secret_key(), algorithms=[_ALGORITHM])
