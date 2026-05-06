from __future__ import annotations

from sqlalchemy import select

from backend.core.security import verify_password
from backend.database import AsyncSessionLocal
from backend.imap.session import ImapSession
from backend.models import Domain, LoginActivity, Mailbox, User


async def run(session: ImapSession, username: str, password: str) -> str:
    normalized = username.strip('"').lower()
    cleaned_password = password.strip('"')

    async with AsyncSessionLocal() as db:
        user_result = await db.execute(select(User).where(User.email == normalized))
        user = user_result.scalar_one_or_none()
        if user is None or not verify_password(cleaned_password, user.hashed_password):
            return "NO authentication failed"
        if not user.is_active:
            return "NO account inactive"

        mailbox_result = await db.execute(select(Mailbox).where(Mailbox.user_id == user.id, Mailbox.is_active == True))
        mailbox = mailbox_result.scalar_one_or_none()
        if mailbox is None:
            return "NO mailbox not provisioned"

        domain_result = await db.execute(select(Domain).where(Domain.id == mailbox.domain_id))
        domain = domain_result.scalar_one_or_none()
        if domain is None or domain.is_suspended:
            return "NO domain suspended"

        mailbox.last_login_at = __import__('datetime').datetime.utcnow()
        db.add(LoginActivity(user_id=user.id, success=True, device_type="imap"))
        await db.commit()

    session.mark_authenticated(normalized, mailbox.maildir_path or "")
    return "* CAPABILITY IMAP4rev1 UIDPLUS IDLE MOVE AUTH=PLAIN AUTH=LOGIN"
