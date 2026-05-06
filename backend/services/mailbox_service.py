"""Mailbox service — create, update, delete, quota checks."""
from __future__ import annotations

import os

from sqlalchemy import select

from backend.config import settings
from backend.core.security import hash_password
from backend.database import AsyncSessionLocal
from backend.models.all_models import Domain, Mailbox, User


async def create_mailbox(
    *,
    domain_id: str,
    local_part: str,
    password: str,
    quota_mb: int = 1024,
) -> dict:
    async with AsyncSessionLocal() as db:
        domain: Domain | None = (
            await db.execute(select(Domain).where(Domain.id == domain_id))
        ).scalar_one_or_none()
        if not domain:
            raise ValueError("Domain not found.")

        full_address = f"{local_part.lower()}@{domain.name.lower()}"

        # Check uniqueness
        existing = await db.scalar(
            select(Mailbox.id).where(Mailbox.full_address == full_address)
        )
        if existing:
            raise ValueError(f"Address {full_address} already exists.")

        user = User(email=full_address, hashed_password=hash_password(password), role="user")
        db.add(user)
        await db.flush()

        maildir = os.path.join(settings.maildir_base, domain.name, local_part)
        mb = Mailbox(
            user_id=user.id,
            domain_id=domain.id,
            local_part=local_part.lower(),
            full_address=full_address,
            quota_mb=quota_mb,
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
