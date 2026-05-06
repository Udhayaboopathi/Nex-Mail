import hashlib
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import ApiKey

router = APIRouter(tags=["api_keys"])


class ApiKeyItem(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    rate_limit_per_hour: int
    expires_at: str | None = None
    last_used_at: str | None = None
    is_active: bool
    created_at: str
    full_key: str | None = None


class CreateApiKeyRequest(BaseModel):
    mailbox_id: str
    domain_id: str
    name: str = Field(min_length=1, max_length=100)
    scopes: list[str] = ["send"]
    rate_limit_per_hour: int = Field(default=1000, ge=1, le=100000)


def _to_item(k: ApiKey, full_key: str | None = None) -> ApiKeyItem:
    return ApiKeyItem(
        id=str(k.id),
        name=k.name or "",
        key_prefix=k.key_prefix or "",
        scopes=list(k.scopes or []),
        rate_limit_per_hour=int(k.rate_limit_per_hour or 1000),
        expires_at=k.expires_at.isoformat() if k.expires_at else None,
        last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
        is_active=bool(k.is_active),
        created_at=k.created_at.isoformat() if k.created_at else "",
        full_key=full_key,
    )


@router.get("/", response_model=list[ApiKeyItem])
async def list_api_keys(user: dict = Depends(require_any_auth)) -> list[ApiKeyItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))).scalars().all()
    return [_to_item(k) for k in rows]


@router.post("/", response_model=ApiKeyItem)
async def create_api_key(payload: CreateApiKeyRequest, user: dict = Depends(require_any_auth)) -> ApiKeyItem:
    try:
        mailbox_uuid = UUID(payload.mailbox_id)
        domain_uuid = UUID(payload.domain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id or domain_id") from exc

    raw_key = f"nm_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    prefix = raw_key[:8]

    async with AsyncSessionLocal() as db:
        api_key = ApiKey(
            mailbox_id=mailbox_uuid,
            domain_id=domain_uuid,
            name=payload.name,
            key_hash=key_hash,
            key_prefix=prefix,
            scopes=payload.scopes,
            rate_limit_per_hour=payload.rate_limit_per_hour,
        )
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)
    return _to_item(api_key, full_key=raw_key)


@router.delete("/{key_id}")
async def delete_api_key(key_id: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        key_uuid = UUID(key_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid key_id") from exc
    async with AsyncSessionLocal() as db:
        key = (await db.execute(select(ApiKey).where(ApiKey.id == key_uuid))).scalar_one_or_none()
        if key is None:
            raise HTTPException(status_code=404, detail="API key not found")
        await db.delete(key)
        await db.commit()
    return {"ok": True}
