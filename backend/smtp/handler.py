from __future__ import annotations

import email
from email.message import Message
from mailbox import Maildir
from pathlib import Path

from sqlalchemy import select

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models import Alias, Domain, Mailbox
from backend.smtp.dkim import verify_message


class InboundHandler:
    async def handle_RCPT(self, _server, _session, envelope, address, _rcpt_options):
        if "@" not in address:
            return "550 invalid recipient"
        local, domain = address.lower().split("@", 1)
        async with AsyncSessionLocal() as db:
            domain_result = await db.execute(select(Domain).where(Domain.name == domain))
            domain_row = domain_result.scalar_one_or_none()
            if domain_row is None or not domain_row.is_active:
                return "550 domain not found"
            if domain_row.is_suspended:
                return "451 domain suspended"
        envelope.rcpt_tos.append(address.lower())
        return "250 OK"

    async def handle_DATA(self, _server, _session, envelope):
        max_bytes = settings.max_message_size_mb * 1024 * 1024
        if len(envelope.content) > max_bytes:
            return "552 message too large"

        parsed = email.message_from_bytes(envelope.content)
        spam_folder = self._folder_for_message(parsed)
        target_folder = spam_folder if spam_folder == "Spam" else "Inbox"

        if not verify_message(envelope.content):
            parsed["X-DKIM-Verify"] = "fail"
        else:
            parsed["X-DKIM-Verify"] = "pass"

        async with AsyncSessionLocal() as db:
            for rcpt in envelope.rcpt_tos:
                resolved = await self._resolve_recipient(db, rcpt)
                if resolved is None:
                    continue
                mailbox, domain = resolved
                if domain.is_suspended:
                    return "451 domain suspended"
                self._store_message(mailbox.maildir_path or self._fallback_maildir(mailbox.full_address), parsed, target_folder)
                mailbox.used_mb = float(mailbox.used_mb or 0) + (len(envelope.content) / (1024 * 1024))
            await db.commit()

        return "250 Message accepted for delivery"

    async def _resolve_recipient(self, db, recipient: str):
        mailbox_result = await db.execute(select(Mailbox).where(Mailbox.full_address == recipient, Mailbox.is_active == True))
        mailbox = mailbox_result.scalar_one_or_none()
        if mailbox is None:
            alias_result = await db.execute(select(Alias).where(Alias.source_address == recipient, Alias.is_active == True))
            alias = alias_result.scalar_one_or_none()
            if alias and alias.destination_address:
                mailbox_result = await db.execute(select(Mailbox).where(Mailbox.full_address == alias.destination_address, Mailbox.is_active == True))
                mailbox = mailbox_result.scalar_one_or_none()
        if mailbox is None:
            return None
        domain_result = await db.execute(select(Domain).where(Domain.id == mailbox.domain_id))
        domain = domain_result.scalar_one_or_none()
        if domain is None:
            return None
        return mailbox, domain

    def _folder_for_message(self, parsed: Message) -> str:
        spam_score = parsed.get("X-Spam-Score")
        if spam_score:
            try:
                if float(spam_score) > 10:
                    return "Spam"
            except ValueError:
                pass
        return "Inbox"

    def _fallback_maildir(self, rcpt: str) -> str:
        mailbox_key = rcpt.strip().lower().replace("@", "_")
        return str(Path(settings.maildir_base) / mailbox_key)

    def _store_message(self, maildir_path: str, parsed: Message, folder: str) -> None:
        root = Path(maildir_path)
        target = root if folder == "Inbox" else root / f".{folder}"
        maildir = Maildir(target.as_posix(), create=True)
        maildir.add(parsed.as_bytes())


class SubmissionHandler(InboundHandler):
    async def handle_AUTH(self, _server, _session, _envelope, mechanism, _auth_data):
        if mechanism not in {"PLAIN", "LOGIN"}:
            return "504 unsupported authentication mechanism"
        return "235 2.7.0 Authentication successful"

    async def handle_EHLO(self, _server, _session, _envelope, _hostname, responses):
        responses.append("250-AUTH LOGIN PLAIN")
        responses.append("250-STARTTLS")
        responses.append("250 SIZE 26214400")
        return responses
