"""
Security utilities: password hashing and JWT token handling.

Uses bcrypt directly (no passlib) to avoid passlib 1.7.x / bcrypt 4.x
compatibility issues.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from backend.config import settings


# ── Password hashing ────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored *hashed* value."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ── JWT tokens ───────────────────────────────────────────────────────────────

def create_token(sub: str, expires_delta: timedelta, extra: dict | None = None) -> str:
    """Encode a JWT with *sub* as the subject, expiring after *expires_delta*."""
    exp = datetime.now(tz=timezone.utc) + expires_delta
    payload: dict = {"sub": sub, "exp": exp}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT, raising JWTError on failure."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
