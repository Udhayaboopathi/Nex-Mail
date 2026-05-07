"""Mailbox service — create, update, delete, quota checks."""
from __future__ import annotations

import os
import re
import uuid

from sqlalchemy import func, select

from backend.config import settings
from backend.core.security import hash_password
from backend.database import AsyncSessionLocal
from backend.models.all_models import Domain, Mailbox, User

_LOCAL_PART_RE = re.compile(r"^[a-z0-9]([a-z0-9._-]{0,62}[a-z0-9])?$|^[a-z0-9]$")


async def create_mailbox(
    *,
    domain_id: str,
    local_part: str,
    password: str,
    quota_mb: int = 1024,
    display_name: str | None = None,
) -> dict:
    local = local_part.strip().lower()
    if not _LOCAL_PART_RE.match(local):
        raise ValueError(
            "Invalid email alias: use 1–64 characters (a-z, 0-9, ., _, -); must start/end with alphanumeric."
        )
    try:
        dom_uuid = uuid.UUID(str(domain_id))
    except ValueError as exc:
        raise ValueError("Invalid domain id.") from exc

    dn = (display_name or "").strip() or None

    async with AsyncSessionLocal() as db:
        domain: Domain | None = (
            await db.execute(select(Domain).where(Domain.id == dom_uuid))
        ).scalar_one_or_none()
        if not domain:
            raise ValueError("Domain not found.")

        pool_mb = max(int(domain.storage_quota_gb or 10), 1) * 1024
        allocated = int(
            await db.scalar(
                select(func.coalesce(func.sum(Mailbox.quota_mb), 0)).where(Mailbox.domain_id == domain.id)
            )
            or 0
        )
        if allocated + int(quota_mb) > pool_mb:
            raise ValueError(
                f"Total mailbox storage would exceed the domain pool ({pool_mb} MB). "
                f"Already allocated: {allocated} MB. Ask super-admin to increase domain storage."
            )

        full_address = f"{local}@{domain.name.lower()}"

        existing = await db.scalar(select(Mailbox.id).where(Mailbox.full_address == full_address))
        if existing:
            raise ValueError(f"Address {full_address} already exists.")

        user = User(email=full_address, hashed_password=hash_password(password), role="user")
        db.add(user)
        await db.flush()

        maildir = os.path.join(settings.maildir_base, domain.name, local)
        mb = Mailbox(
            user_id=user.id,
            domain_id=domain.id,
            local_part=local,
            display_name=dn,
            full_address=full_address,
            quota_mb=int(quota_mb),
            maildir_path=maildir,
        )
        db.add(mb)
        await db.commit()
        await db.refresh(mb)

    return {
        "id": str(mb.id),
        "full_address": mb.full_address,
        "quota_mb": mb.quota_mb,
        "is_active": mb.is_active,
        "display_name": mb.display_name,
    }


async def set_mailbox_password(mailbox_id: str, new_password: str) -> None:
    async with AsyncSessionLocal() as db:
        mb: Mailbox | None = (
            await db.execute(select(Mailbox).where(Mailbox.id == mailbox_id))
        ).scalar_one_or_none()
        if not mb:
            raise ValueError("Mailbox not found.")
        user: User | None = (
            await db.execute(select(User).where(User.id == mb.user_id))
        ).scalar_one_or_none()
        if user:
            user.hashed_password = hash_password(new_password)
        await db.commit()


async def get_mailbox_usage(mailbox_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        mb: Mailbox | None = (
            await db.execute(select(Mailbox).where(Mailbox.id == mailbox_id))
        ).scalar_one_or_none()
        if not mb:
            raise ValueError("Mailbox not found.")
        return {
            "used_mb": float(mb.used_mb or 0),
            "quota_mb": float(mb.quota_mb or 1024),
            "percent": round(float(mb.used_mb or 0) / max(float(mb.quota_mb or 1), 1) * 100, 1),
        }
