"""Mail service — folder listings, email CRUD, search."""
from __future__ import annotations

from sqlalchemy import func, or_, select

from backend.database import AsyncSessionLocal
from backend.models.all_models import Email, Label, Mailbox


# Standard IMAP-style system folders
SYSTEM_FOLDERS = ["INBOX", "Sent", "Drafts", "Spam", "Trash", "Archive"]


async def list_folders(mailbox_id: str) -> list[dict]:
    """Return system folders plus any label-backed custom folders with counts."""
    async with AsyncSessionLocal() as db:
        results = []
        for folder in SYSTEM_FOLDERS:
            total = int(
                await db.scalar(
                    select(func.count(Email.id)).where(
                        Email.mailbox_id == mailbox_id,
                        Email.folder == folder,
                        Email.is_deleted == False,
                    )
                )
                or 0
            )
            unread = int(
                await db.scalar(
                    select(func.count(Email.id)).where(
                        Email.mailbox_id == mailbox_id,
                        Email.folder == folder,
                        Email.is_read == False,
                        Email.is_deleted == False,
                    )
                )
                or 0
            )
            results.append({"name": folder, "total": total, "unread": unread})

        # Custom labels as virtual folders
        labels = (
            await db.execute(
                select(Label).where(Label.mailbox_id == mailbox_id)
            )
        ).scalars().all()
        for lbl in labels:
            results.append({"name": lbl.name, "total": 0, "unread": 0, "color": lbl.color})

    return results


async def list_emails(
    mailbox_id: str,
    folder: str = "INBOX",
    page: int = 1,
    per_page: int = 50,
) -> dict:
    """Return a paginated list of emails for a folder."""
    async with AsyncSessionLocal() as db:
        base_q = (
            select(Email)
            .where(
                Email.mailbox_id == mailbox_id,
                Email.folder == folder,
                Email.is_deleted == False,
            )
            .order_by(Email.sent_at.desc())
        )
        total = int(await db.scalar(select(func.count()).select_from(base_q.subquery())) or 0)
        rows = (
            await db.execute(base_q.offset((page - 1) * per_page).limit(per_page))
        ).scalars().all()

    items = [_email_to_dict(e) for e in rows]
    return {"items": items, "total": total, "page": page, "per_page": per_page}


async def get_email(mailbox_id: str, email_id: str) -> dict | None:
    async with AsyncSessionLocal() as db:
        email: Email | None = (
            await db.execute(
                select(Email).where(
                    Email.id == email_id,
                    Email.mailbox_id == mailbox_id,
                    Email.is_deleted == False,
                )
            )
        ).scalar_one_or_none()
        if not email:
            return None
        if not email.is_read:
            email.is_read = True
            await db.commit()
    return _email_to_dict(email)


async def mark_emails(
    mailbox_id: str,
    email_ids: list[str],
    *,
    is_read: bool | None = None,
    is_starred: bool | None = None,
    folder: str | None = None,
    is_deleted: bool | None = None,
) -> int:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(Email).where(
                    Email.id.in_(email_ids),
                    Email.mailbox_id == mailbox_id,
                )
            )
        ).scalars().all()
        for email in rows:
            if is_read is not None:
                email.is_read = is_read
            if is_starred is not None:
                email.is_starred = is_starred
            if folder is not None:
                email.folder = folder
            if is_deleted is not None:
                email.is_deleted = is_deleted
        await db.commit()
    return len(rows)


async def search_emails(mailbox_id: str, query: str, limit: int = 20) -> list[dict]:
    async with AsyncSessionLocal() as db:
        q = query.strip()
        rows = (
            await db.execute(
                select(Email)
                .where(
                    Email.mailbox_id == mailbox_id,
                    Email.is_deleted == False,
                    or_(
                        Email.subject.ilike(f"%{q}%"),
                        Email.from_address.ilike(f"%{q}%"),
                        Email.body_text.ilike(f"%{q}%"),
                    ),
                )
                .order_by(Email.sent_at.desc())
                .limit(limit)
            )
        ).scalars().all()
    return [_email_to_dict(e) for e in rows]


def _email_to_dict(e: Email) -> dict:
    return {
        "id": str(e.id),
        "message_id": e.message_id or "",
        "thread_id": str(e.thread_id) if e.thread_id else None,
        "mailbox_id": str(e.mailbox_id),
        "folder": e.folder or "INBOX",
        "subject": e.subject or "(no subject)",
        "from_address": e.from_address or "",
        "to_addresses": e.to_addresses or [],
        "cc_addresses": e.cc_addresses or [],
        "bcc_addresses": e.bcc_addresses or [],
        "body_text": e.body_text or "",
        "body_html": e.body_html or "",
        "is_read": bool(e.is_read),
        "is_starred": bool(e.is_starred),
        "is_deleted": bool(e.is_deleted),
        "has_attachments": bool(e.has_attachments),
        "sent_at": e.sent_at.isoformat() if e.sent_at else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
