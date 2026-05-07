from __future__ import annotations

import asyncio
import email
import logging
from email.message import Message
from mailbox import Maildir
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database_sync import SessionLocalSync
from backend.models import Alias, Domain, Mailbox
from backend.smtp.dkim import verify_message

logger = logging.getLogger(__name__)


def _fallback_maildir_path(rcpt: str) -> str:
    mailbox_key = rcpt.strip().lower().replace("@", "_")
    return str(Path(settings.maildir_base) / mailbox_key)


def _store_to_maildir(maildir_path: str, parsed: Message, folder: str) -> None:
    root = Path(maildir_path)
    # Ensure Maildir root and standard subfolders exist before creating the mailbox.
    root.mkdir(parents=True, exist_ok=True)
    for sub in ("cur", "new", "tmp"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    target = root if folder == "Inbox" else root / f".{folder}"
    target.mkdir(parents=True, exist_ok=True)
    maildir = Maildir(target.as_posix(), create=True)
    maildir.add(parsed.as_bytes())


def _resolve_recipient_sync(db: Session, recipient: str):
    mailbox = db.scalar(
        select(Mailbox).where(Mailbox.full_address == recipient, Mailbox.is_active == True)
    )
    if mailbox is None:
        alias = db.scalar(select(Alias).where(Alias.source_address == recipient, Alias.is_active == True))
        if alias and alias.destination_address:
            mailbox = db.scalar(
                select(Mailbox).where(
                    Mailbox.full_address == alias.destination_address,
                    Mailbox.is_active == True,
                )
            )
    if mailbox is None:
        return None
    domain = db.scalar(select(Domain).where(Domain.id == mailbox.domain_id))
    if domain is None:
        return None
    return mailbox, domain


def _check_rcpt_sync(domain: str) -> str | None:
    """Return SMTP error string or None if OK."""
    with SessionLocalSync() as db:
        domain_row = db.scalar(select(Domain).where(Domain.name == domain))
        if domain_row is None or not domain_row.is_active:
            return "550 domain not found"
        if domain_row.is_suspended:
            return "451 domain suspended"
    return None


def _partition_local_remote(rcpts: list[str]) -> tuple[list[str], list[str]]:
    """Recipients we host (mailbox exists) vs relay to the internet."""
    local: list[str] = []
    remote: list[str] = []
    with SessionLocalSync() as db:
        for r in rcpts:
            if _resolve_recipient_sync(db, r) is not None:
                local.append(r)
            else:
                remote.append(r)
    return local, remote


def _deliver_data_sync(envelope_rcpt_tos: list[str], envelope_content: bytes, parsed: Message, target_folder: str) -> str | None:
    """Return SMTP error string or None on success."""
    max_bytes = settings.max_message_size_mb * 1024 * 1024
    if len(envelope_content) > max_bytes:
        return "552 message too large"

    with SessionLocalSync() as db:
        for rcpt in envelope_rcpt_tos:
            resolved = _resolve_recipient_sync(db, rcpt)
            if resolved is None:
                continue
            mailbox, domain = resolved
            if domain.is_suspended:
                return "451 domain suspended"
            _store_to_maildir(
                mailbox.maildir_path or _fallback_maildir_path(mailbox.full_address),
                parsed,
                target_folder,
            )
            mailbox.used_mb = float(mailbox.used_mb or 0) + (len(envelope_content) / (1024 * 1024))
        db.commit()
    return None


class InboundHandler:
    async def handle_RCPT(self, _server, _session, envelope, address, _rcpt_options):
        if "@" not in address:
            return "550 invalid recipient"
        _local, domain = address.lower().split("@", 1)
        err = await asyncio.to_thread(_check_rcpt_sync, domain)
        if err:
            return err
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

        err = await asyncio.to_thread(
            _deliver_data_sync,
            list(envelope.rcpt_tos),
            envelope.content,
            parsed,
            target_folder,
        )
        if err:
            return err
        return "250 Message accepted for delivery"

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
        return _fallback_maildir_path(rcpt)

    def _store_message(self, maildir_path: str, parsed: Message, folder: str) -> None:
        _store_to_maildir(maildir_path, parsed, folder)


class SubmissionHandler(InboundHandler):
    """Authenticated submission: RCPT may be external; DATA relays via main-loop async MX delivery."""

    async def handle_RCPT(self, _server, _session, envelope, address, _rcpt_options):
        if "@" not in address:
            return "550 invalid recipient"
        envelope.rcpt_tos.append(address.lower())
        return "250 OK"

    async def handle_DATA(self, _server, _session, envelope):
        mail_from = envelope.mail_from
        if not mail_from:
            return "503 Error: need MAIL command"
        mail_from = mail_from.strip()
        if mail_from.startswith("<") and mail_from.endswith(">"):
            mail_from = mail_from[1:-1].strip()
        max_bytes = settings.max_message_size_mb * 1024 * 1024
        raw = envelope.content
        if isinstance(raw, str):
            raw = raw.encode("utf-8", errors="surrogateescape")
        if len(raw) > max_bytes:
            return "552 message too large"

        local_rcpts, remote_rcpts = await asyncio.to_thread(_partition_local_remote, list(envelope.rcpt_tos))

        if local_rcpts:
            parsed = email.message_from_bytes(raw)
            spam_folder = self._folder_for_message(parsed)
            target_folder = spam_folder if spam_folder == "Spam" else "Inbox"
            if not verify_message(raw):
                parsed["X-DKIM-Verify"] = "fail"
            else:
                parsed["X-DKIM-Verify"] = "pass"
            err = await asyncio.to_thread(_deliver_data_sync, local_rcpts, raw, parsed, target_folder)
            if err:
                return err

        if remote_rcpts:
            # Do not await relay: aiosmtplib (and the HTTP mail-test client) would block until MX
            # delivery finishes, often exceeding client timeouts when :25 is slow or blocked.
            from backend.runtime import get_main_loop
            from backend.smtp.outbound import SMTPDeliveryError, relay_mx_raw

            loop = get_main_loop()

            async def _relay_bg() -> None:
                logger.info('Submission background relay starting mail_from=%s recipients=%s', mail_from, remote_rcpts)
                try:
                    await relay_mx_raw(mail_from, remote_rcpts, raw)
                    logger.info('Submission background relay finished OK mail_from=%s recipients=%s', mail_from, remote_rcpts)
                except SMTPDeliveryError as exc:
                    logger.error(
                        "Submission relay failed (mail_from=%s recipients=%s): %s",
                        mail_from,
                        remote_rcpts,
                        exc,
                    )
                except Exception:
                    logger.exception(
                        "Submission relay error (mail_from=%s recipients=%s)",
                        mail_from,
                        remote_rcpts,
                    )
                finally:
                    logger.info(
                        'Submission background relay task ended mail_from=%s recipients=%s',
                        mail_from,
                        remote_rcpts,
                    )

            def _schedule() -> None:
                task = loop.create_task(_relay_bg())

                def _swallow_task_result(t: asyncio.Task) -> None:
                    try:
                        t.result()
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        pass

                task.add_done_callback(_swallow_task_result)

            loop.call_soon_threadsafe(_schedule)

        return "250 Message accepted for delivery"
