from __future__ import annotations

import asyncio
import logging
import uuid
from email.message import EmailMessage
from email.utils import make_msgid

import aiosmtplib
import dns.resolver
from sqlalchemy import select

from backend.config import settings
from backend.core.encryption import decrypt_value
from backend.database import AsyncSessionLocal
from backend.models import Domain, Email, Mailbox, UnsubscribeList
from backend.smtp.dkim import sign_message

logger = logging.getLogger(__name__)

# Per-connection timeout so blocked outbound :25 does not hang the HTTP request indefinitely.
SMTP_CLIENT_TIMEOUT = 25.0


class SMTPDeliveryError(Exception):
    """Raised when SMTP direct delivery fails for all recipients."""


async def _resolve_mx_hosts(domain: str) -> list[tuple[int, str]]:
    """MX lookup in a thread so the asyncio loop (FastAPI + aiosmtplib client) is not blocked."""

    def _sync() -> list[tuple[int, str]]:
        mx_records = dns.resolver.resolve(domain, 'MX')
        return sorted([(r.preference, str(r.exchange).rstrip('.')) for r in mx_records], key=lambda x: x[0])

    return await asyncio.to_thread(_sync)


def _smtp_delivery_hint() -> str:
    return (
        ' Nex Mail delivers outbound by connecting to each recipient domain’s MX on TCP 25. Many VPS providers block '
        'outbound port 25 — ask yours to lift the block or use a host that allows it. For inbox placement, set PTR '
        '(reverse DNS) for your sending IP to match SMTP_HOSTNAME, publish SPF/DKIM/DMARC for the From domain, and '
        'avoid new IPs sending high volume immediately.'
    )


async def _is_unsubscribed(sender_mailbox_id, recipient: str) -> bool:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UnsubscribeList).where(
                UnsubscribeList.sender_mailbox_id == sender_mailbox_id,
                UnsubscribeList.recipient_email == recipient,
            )
        )
        return result.scalar_one_or_none() is not None


def _dkim_domain_for_from(from_addr: str) -> str:
    forced = (settings.dkim_signing_domain or "").strip().lower().rstrip(".")
    if forced:
        return forced[5:] if forced.startswith("mail.") else forced
    return from_addr.split("@")[-1].lower().strip()


def _forced_dkim_signing_enabled() -> bool:
    return bool((settings.dkim_signing_domain or "").strip())


def _sender_domain(from_addr: str) -> str:
    return from_addr.split("@")[-1].lower().strip()


def _envelope_from_for_signing(from_addr: str, signing_domain: str) -> str:
    """
    Envelope MAIL FROM used for SMTP transaction.
    When global signing is forced to another domain, align envelope sender domain
    so SPF can pass for that domain at receiver side.
    """
    sender_domain = _sender_domain(from_addr)
    if sender_domain == signing_domain:
        return from_addr
    local = from_addr.split("@", 1)[0].strip() or "mailer"
    return f"{local}@{signing_domain}"


async def _effective_dkim_domain(from_addr: str) -> str:
    forced = _dkim_domain_for_from(from_addr)
    if not _forced_dkim_signing_enabled():
        return forced

    sender_domain = _sender_domain(from_addr)
    if sender_domain == forced:
        return forced

    async with AsyncSessionLocal() as db:
        sender_row = (await db.execute(select(Domain).where(Domain.name == sender_domain))).scalar_one_or_none()
    # Super-admin override: unlock this sender domain to sign with its own key.
    if sender_row is not None and bool(sender_row.allow_custom_dkim_signing):
        return sender_domain
    return forced


async def _load_dkim_key(domain_name: str) -> tuple[str, bytes] | None:
    async with AsyncSessionLocal() as db:
        domain_result = await db.execute(select(Domain).where(Domain.name == domain_name))
        domain = domain_result.scalar_one_or_none()
        if domain is None or not domain.dkim_private_key_encrypted:
            return None
        pem = decrypt_value(domain.dkim_private_key_encrypted)
        return (domain.dkim_selector or "mail", pem.encode())


def _build_message(from_addr: str, to_list: list[str], subject: str, body_text: str, body_html: str | None, attachments: list[dict] | None, headers: dict[str, str] | None) -> EmailMessage:
    msg = EmailMessage()
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_list)
    msg['Subject'] = subject
    msg['Message-ID'] = make_msgid()
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype='html')
    for k, v in (headers or {}).items():
        msg[k] = v
    for attachment in attachments or []:
        content = attachment.get('content', b'')
        if isinstance(content, str):
            content = content.encode()
        msg.add_attachment(content, maintype=attachment.get('maintype', 'application'), subtype=attachment.get('subtype', 'octet-stream'), filename=attachment.get('filename', 'attachment.bin'), disposition='attachment')
    return msg


async def send_direct(from_addr: str, to_list: list[str], subject: str, body_text: str, body_html: str | None = None, attachments: list[dict] | None = None, headers: dict[str, str] | None = None) -> dict[str, object]:
    msg = _build_message(from_addr, to_list, subject, body_text, body_html, attachments, headers)

    sender_mailbox_id = None
    async with AsyncSessionLocal() as db:
        mailbox_result = await db.execute(select(Mailbox).where(Mailbox.full_address == from_addr.lower()))
        mailbox = mailbox_result.scalar_one_or_none()
        if mailbox is not None:
            sender_mailbox_id = mailbox.id

    signing_domain = await _effective_dkim_domain(from_addr)
    envelope_from = _envelope_from_for_signing(from_addr, signing_domain)
    dkim_data = await _load_dkim_key(signing_domain)
    if _forced_dkim_signing_enabled() and signing_domain == _dkim_domain_for_from(from_addr) and dkim_data is None:
        forced_domain = signing_domain
        raise SMTPDeliveryError(
            f"Forced DKIM signing is enabled but no DKIM key is configured for '{forced_domain}'."
        )
    raw = msg.as_bytes()
    if dkim_data:
        selector, private_key = dkim_data
        raw = sign_message(raw, selector, signing_domain, private_key)

    failed: list[str] = []
    for recipient in to_list:
        if sender_mailbox_id and await _is_unsubscribed(sender_mailbox_id, recipient):
            failed.append(recipient)
            continue

        domain = recipient.split('@')[-1]
        delivered = False
        try:
            logger.info('send_direct MX lookup domain=%s recipient=%s', domain, recipient)
            mx_hosts = await _resolve_mx_hosts(domain)
        except Exception as exc:
            raise SMTPDeliveryError(f'MX lookup failed for {recipient}: {exc}') from exc

        for _, mx_host in mx_hosts:
            try:
                logger.info(
                    'send_direct trying MX mail_from=%s envelope_from=%s to=%s mx=%s:25',
                    from_addr,
                    envelope_from,
                    recipient,
                    mx_host,
                )
                await aiosmtplib.send(
                    raw,
                    sender=envelope_from,
                    recipients=[recipient],
                    hostname=mx_host,
                    port=25,
                    start_tls=True,
                    timeout=SMTP_CLIENT_TIMEOUT,
                )
                delivered = True
                logger.info(
                    'Outbound delivered via direct MX mail_from=%s to=%s mx=%s',
                    from_addr,
                    recipient,
                    mx_host,
                )
                break
            except Exception as exc:
                logger.info('send_direct MX try failed mx=%s to=%s: %s', mx_host, recipient, exc)
                continue

        if not delivered:
            failed.append(recipient)

    if failed and len(failed) == len(to_list):
        raise SMTPDeliveryError(f'Failed all recipients: {failed}.{_smtp_delivery_hint()}')

    # Persist sender-side Sent copy in DB.
    if sender_mailbox_id is not None:
        delivered_to = [r for r in to_list if r not in failed]
        async with AsyncSessionLocal() as db:
            db.add(
                Email(
                    id=uuid.uuid4(),
                    mailbox_id=sender_mailbox_id,
                    folder="sent",
                    from_address=from_addr,
                    to_addresses=to_list,
                    cc_addresses=[],
                    bcc_addresses=[],
                    subject=subject,
                    body_text=body_text,
                    body_html=body_html,
                    message_id=str(msg.get("Message-ID") or ""),
                    flags=["S"],
                    is_read=True,
                    is_flagged=False,
                    has_attachments=bool(attachments),
                    headers={"delivered_to": delivered_to, "failed_recipients": failed},
                )
            )
            await db.commit()

    return {'success': len(failed) == 0, 'message_id': msg['Message-ID'], 'failed_recipients': failed}


async def relay_mx_raw(mail_from: str, recipients: list[str], raw: bytes) -> None:
    """
    Deliver an RFC822 payload per recipient via each domain’s MX on port 25.
    Used by authenticated SMTP submission for non-local addresses. Must run on the FastAPI event loop.
    """
    if not recipients:
        return
    logger.info('relay_mx_raw start mail_from=%s recipients=%s', mail_from, recipients)
    signing_domain = await _effective_dkim_domain(mail_from)
    envelope_from = _envelope_from_for_signing(mail_from, signing_domain)
    dkim_data = await _load_dkim_key(signing_domain)
    if _forced_dkim_signing_enabled() and signing_domain == _dkim_domain_for_from(mail_from) and dkim_data is None:
        forced_domain = signing_domain
        raise SMTPDeliveryError(
            f"Forced DKIM signing is enabled but no DKIM key is configured for '{forced_domain}'."
        )
    logger.info('relay_mx_raw after DKIM mail_from=%s signed=%s', mail_from, bool(dkim_data))
    out = raw
    if dkim_data:
        selector, private_key = dkim_data
        out = sign_message(out, selector, signing_domain, private_key)

    sender_mailbox_id = None
    async with AsyncSessionLocal() as db:
        mailbox_result = await db.execute(select(Mailbox).where(Mailbox.full_address == mail_from.lower()))
        mailbox = mailbox_result.scalar_one_or_none()
        if mailbox is not None:
            sender_mailbox_id = mailbox.id

    failed: list[str] = []
    for recipient in recipients:
        if sender_mailbox_id and await _is_unsubscribed(sender_mailbox_id, recipient):
            failed.append(recipient)
            continue
        domain = recipient.split('@')[-1]
        delivered = False
        try:
            logger.info('relay_mx_raw MX lookup domain=%s recipient=%s', domain, recipient)
            mx_hosts = await _resolve_mx_hosts(domain)
        except Exception as exc:
            raise SMTPDeliveryError(f'MX lookup failed for {recipient}: {exc}') from exc

        for _, mx_host in mx_hosts:
            try:
                logger.info(
                    'relay_mx_raw trying MX mail_from=%s envelope_from=%s to=%s mx=%s:25',
                    mail_from,
                    envelope_from,
                    recipient,
                    mx_host,
                )
                await aiosmtplib.send(
                    out,
                    sender=envelope_from,
                    recipients=[recipient],
                    hostname=mx_host,
                    port=25,
                    start_tls=True,
                    timeout=SMTP_CLIENT_TIMEOUT,
                )
                delivered = True
                logger.info(
                    'Outbound delivered via direct MX mail_from=%s to=%s mx=%s',
                    mail_from,
                    recipient,
                    mx_host,
                )
                break
            except Exception as exc:
                logger.info('relay_mx_raw MX try failed mx=%s to=%s: %s', mx_host, recipient, exc)
                continue

        if not delivered:
            failed.append(recipient)

    if failed:
        ok = [r for r in recipients if r not in failed]
        if ok:
            logger.warning(
                'relay_mx_raw partial failure: not delivered to %s (delivered to %s, mail_from=%s)',
                failed,
                ok,
                mail_from,
            )
    if failed and len(failed) == len(recipients):
        raise SMTPDeliveryError(f'Failed all recipients: {failed}.{_smtp_delivery_hint()}')
    if not failed:
        logger.info('relay_mx_raw completed mail_from=%s recipients=%s', mail_from, recipients)


async def send_email(to: list[str] | str, subject: str, body_text: str, body_html: str | None = None, **kwargs: object) -> dict[str, object]:
    recipients = [to] if isinstance(to, str) else to
    return await send_direct(
        from_addr=str(kwargs.get('from_addr', 'no-reply@localhost')),
        to_list=recipients,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        attachments=kwargs.get('attachments') if isinstance(kwargs.get('attachments'), list) else None,
        headers=kwargs.get('headers') if isinstance(kwargs.get('headers'), dict) else None,
    )
