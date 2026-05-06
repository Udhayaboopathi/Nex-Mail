from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

import aiosmtplib
import dns.resolver
from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import Domain, Mailbox, UnsubscribeList
from backend.smtp.dkim import sign_message


class SMTPDeliveryError(Exception):
    """Raised when SMTP direct delivery fails for all recipients."""


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
        return (domain.dkim_selector, domain.dkim_private_key_encrypted.encode())


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
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_hosts = sorted([(r.preference, str(r.exchange).rstrip('.')) for r in mx_records], key=lambda x: x[0])
        except Exception as exc:
            raise SMTPDeliveryError(f'MX lookup failed for {recipient}: {exc}') from exc

        delivered = False
        for _, mx_host in mx_hosts:
            try:
                await aiosmtplib.send(raw, sender=from_addr, recipients=[recipient], hostname=mx_host, port=25, start_tls=True)
                delivered = True
                break
            except Exception:
                continue

        if not delivered:
            failed.append(recipient)

    if failed and len(failed) == len(to_list):
        raise SMTPDeliveryError(f'Failed all recipients: {failed}')

    return {'success': len(failed) == 0, 'message_id': msg['Message-ID'], 'failed_recipients': failed}


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
