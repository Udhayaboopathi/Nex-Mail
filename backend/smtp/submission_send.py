"""Send mail via authenticated SMTP submission (e.g. port 587 + STARTTLS)."""

from __future__ import annotations

from email.message import EmailMessage
from email.utils import formatdate, make_msgid

import aiosmtplib


class SubmissionSMTPError(Exception):
    """Raised when submission SMTP send fails."""


async def send_via_submission(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    mail_from: str,
    mail_to: str,
    subject: str,
    body_text: str,
    use_starttls: bool = True,
    timeout: float = 30.0,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.set_content(body_text)

    try:
        await aiosmtplib.send(
            msg,
            hostname=host.strip(),
            port=port,
            username=username.strip(),
            password=password,
            start_tls=use_starttls,
            timeout=timeout,
        )
    except Exception as exc:
        parts: list[str] = [f"{type(exc).__name__}: {exc}"]
        code = getattr(exc, "smtp_code", None)
        if code is not None:
            parts.append(f"smtp_code={code}")
        detail = getattr(exc, "smtp_detail", None)
        if detail:
            parts.append(f"smtp_detail={detail!r}")
        if exc.__cause__:
            parts.append(f"cause={exc.__cause__!r}")
        raise SubmissionSMTPError(" | ".join(parts)) from exc
