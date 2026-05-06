from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

import aiosmtplib
import dns.resolver
from sqlalchemy import select

from backend.config import settings
from backend.core.encryption import decrypt_value
from backend.database import AsyncSessionLocal
from backend.models import Domain, Mailbox, UnsubscribeList
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
    if (settings.smtp_outbound_relay_host or '').strip():
        return ' Direct MX was exhausted; check SMTP_OUTBOUND_RELAY_* credentials and provider logs if smarthost also failed.'
    return (
        ' Many hosts block outbound TCP 25. Set SMTP_OUTBOUND_RELAY_HOST (and user/password) as a fallback smarthost '
        'after direct MX fails.'
    )


def outbound_relay_uses_implicit_tls() -> bool:
    if bool(getattr(settings, 'smtp_outbound_relay_implicit_tls', False)):
        return True
    return int(settings.smtp_outbound_relay_port) == 465


async def _try_outbound_smarthost(mail_from: str, recipient: str, raw: bytes) -> bool:
    host = (settings.smtp_outbound_relay_host or '').strip()
    if not host:
        return False
    user = (settings.smtp_outbound_relay_user or '').strip()
    pw = settings.smtp_outbound_relay_password or ''
    port = int(settings.smtp_outbound_relay_port)
    implicit = outbound_relay_uses_implicit_tls()
    kwargs: dict = {
        'hostname': host,
        'port': port,
        'timeout': SMTP_CLIENT_TIMEOUT,
    }
    if implicit:
        kwargs['use_tls'] = True
        kwargs['start_tls'] = False
    else:
        kwargs['start_tls'] = bool(settings.smtp_outbound_relay_use_tls)
    if user:
        kwargs['username'] = user
        kwargs['password'] = pw
    try:
        await aiosmtplib.send(raw, sender=mail_from, recipients=[recipient], **kwargs)
        logger.info(
            'Outbound delivered via smarthost %s:%s mail_from=%s to=%s',
            host,
            kwargs['port'],
            mail_from,
            recipient,
        )
        return True
    except Exception as exc:
        logger.warning('Outbound smarthost %s:%s → %s failed: %s', host, kwargs['port'], recipient, exc)
        return False


async def _is_unsubscribed(sender_mailbox_id, recipient: str) -> bool:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UnsubscribeList).where(
                UnsubscribeList.sender_mailbox_id == sender_mailbox_id,
                UnsubscribeList.recipient_email == recipient,
            )
        )
        return result.scalar_one_or_none() is not None


async def _load_dkim_key(from_addr: str) -> tuple[str, bytes] | None:
    domain_name = from_addr.split('@')[-1].lower()
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

    dkim_data = await _load_dkim_key(from_addr)
    raw = msg.as_bytes()
    if dkim_data:
        selector, private_key = dkim_data
        raw = sign_message(raw, selector, from_addr.split('@')[-1], private_key)

    failed: list[str] = []
    for recipient in to_list:
        if sender_mailbox_id and await _is_unsubscribed(sender_mailbox_id, recipient):
            failed.append(recipient)
            continue

        domain = recipient.split('@')[-1]
        try:
            logger.info('send_direct MX lookup domain=%s recipient=%s', domain, recipient)
            mx_hosts = await _resolve_mx_hosts(domain)
        except Exception as exc:
            raise SMTPDeliveryError(f'MX lookup failed for {recipient}: {exc}') from exc

        delivered = False
        for _, mx_host in mx_hosts:
            try:
                logger.info(
                    'send_direct trying MX mail_from=%s to=%s mx=%s:25',
                    from_addr,
                    recipient,
                    mx_host,
                )
                await aiosmtplib.send(
                    raw,
                    sender=from_addr,
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

        if not delivered and (settings.smtp_outbound_relay_host or '').strip():
            logger.info('Direct MX failed for %s; trying smarthost for mail_from=%s', recipient, from_addr)
            delivered = await _try_outbound_smarthost(from_addr, recipient, raw)

        if not delivered:
            failed.append(recipient)

    if failed and len(failed) == len(to_list):
        raise SMTPDeliveryError(f'Failed all recipients: {failed}.{_smtp_delivery_hint()}')

    return {'success': len(failed) == 0, 'message_id': msg['Message-ID'], 'failed_recipients': failed}


async def relay_mx_raw(mail_from: str, recipients: list[str], raw: bytes) -> None:
    """
    Deliver an RFC822 payload per recipient: try their MX on port 25 first, then SMTP_OUTBOUND_RELAY_* if set and MX failed.
    Used by authenticated SMTP submission for non-local addresses. Must run on the FastAPI event loop.
    """
    if not recipients:
        return
    logger.info('relay_mx_raw start mail_from=%s recipients=%s', mail_from, recipients)
    dkim_data = await _load_dkim_key(mail_from)
    logger.info('relay_mx_raw after DKIM mail_from=%s signed=%s', mail_from, bool(dkim_data))
    out = raw
    if dkim_data:
        selector, private_key = dkim_data
        out = sign_message(out, selector, mail_from.split('@')[-1].lower(), private_key)

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
        try:
            logger.info('relay_mx_raw MX lookup domain=%s recipient=%s', domain, recipient)
            mx_hosts = await _resolve_mx_hosts(domain)
        except Exception as exc:
            raise SMTPDeliveryError(f'MX lookup failed for {recipient}: {exc}') from exc

        delivered = False
        for _, mx_host in mx_hosts:
            try:
                logger.info(
                    'relay_mx_raw trying MX mail_from=%s to=%s mx=%s:25',
                    mail_from,
                    recipient,
                    mx_host,
                )
                await aiosmtplib.send(
                    out,
                    sender=mail_from,
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

        if not delivered and (settings.smtp_outbound_relay_host or '').strip():
            logger.info('Direct MX failed for %s; trying smarthost for mail_from=%s', recipient, mail_from)
            delivered = await _try_outbound_smarthost(mail_from, recipient, out)

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
