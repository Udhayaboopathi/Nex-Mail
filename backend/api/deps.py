"""
Dependency helpers shared across all routers.

  get_db              — yields an AsyncSession
  get_current_user    — returns {"id": ..., "role": ..., "email": ...}
  require_role(...)   — factory that raises 403 if the caller's role isn't in the set
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import decode_token
from backend.database import AsyncSessionLocal

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = decode_token(token)
        if payload.get("totp_pending"):
            raise HTTPException(status_code=401, detail="Complete TOTP verification first.")
        return {
            "id": payload.get("sub", ""),
            "role": payload.get("role", "user"),
            "email": payload.get("email", ""),
        }
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token.") from exc


def require_role(*roles: str):
    """
    Usage:
        @router.get("/admin")
        async def admin(user=Depends(require_role("super_admin", "domain_admin"))):
            ...
    """

    async def _check(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of roles: {', '.join(roles)}.",
            )
        return user

    return _check


# Pre-built role guards for convenience
require_super_admin = require_role("super_admin")
require_domain_admin = require_role("domain_admin", "super_admin")
require_any_auth = get_current_user
