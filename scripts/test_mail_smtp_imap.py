#!/usr/bin/env python3
"""
Send a test email over SMTP and optionally check IMAP (SSL).

Fill in your real server values via environment variables or CLI flags.
This does not use Nex Mail's direct-MX path — it uses normal authenticated SMTP.

Examples (PowerShell):

  $env:TEST_SMTP_HOST="mail.sudoinnovation.tech"
  $env:TEST_SMTP_PORT="587"
  $env:TEST_SMTP_USER="you@udhayaboopathi.tech"
  $env:TEST_SMTP_PASSWORD="secret"
  $env:TEST_TO="udhayaboopathi2003@gmail.com"
  python scripts/test_mail_smtp_imap.py

  python scripts/test_mail_smtp_imap.py --smtp-host mail.example.com --smtp-user u@example.com \\
    --smtp-password pass --to friend@gmail.com --imap-host mail.example.com

If a `.env` file exists in the project root, simple KEY=value lines are loaded (no shell export needed).
"""

from __future__ import annotations

import argparse
import imaplib
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path


def _load_dotenv_simple(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def _env(key: str, default: str | None = None) -> str | None:
    v = os.environ.get(key)
    if v is not None and v.strip() != "":
        return v
    return default


def send_smtp(
    host: str,
    port: int,
    user: str,
    password: str,
    mail_from: str,
    mail_to: str,
    subject: str,
    use_starttls: bool,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg.set_content(
        "Nex Mail SMTP connectivity test.\n\n"
        "If you received this, authenticated submission to your server works.\n"
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.ehlo()
        if use_starttls:
            smtp.starttls(context=context)
            smtp.ehlo()
        smtp.login(user, password)
        smtp.send_message(msg)


def check_imap(host: str, port: int, user: str, password: str) -> None:
    context = ssl.create_default_context()
    with imaplib.IMAP4_SSL(host, port, ssl_context=context, timeout=30) as imap:
        imap.login(user, password)
        imap.select("INBOX", readonly=True)
        typ, data = imap.search(None, "ALL")
        if typ != "OK":
            raise RuntimeError(f"IMAP SEARCH failed: {typ} {data}")
        count = len(data[0].split()) if data and data[0] else 0
        print(f"IMAP OK — INBOX has about {count} message(s) (by sequence search).")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    _load_dotenv_simple(root / ".env")

    p = argparse.ArgumentParser(description="Test SMTP send + optional IMAP login")
    p.add_argument("--smtp-host", default=_env("TEST_SMTP_HOST", "localhost"))
    p.add_argument("--smtp-port", type=int, default=int(_env("TEST_SMTP_PORT", "587") or "587"))
    p.add_argument("--smtp-user", default=_env("TEST_SMTP_USER"))
    p.add_argument("--smtp-password", default=_env("TEST_SMTP_PASSWORD"))
    p.add_argument("--from-addr", default=_env("TEST_FROM"), help="Defaults to SMTP user")
    p.add_argument("--to", default=_env("TEST_TO"), help="Recipient address")
    p.add_argument("--no-starttls", action="store_true", help="Use plain SMTP (not typical on 587)")
    p.add_argument("--subject", default=_env("TEST_SUBJECT", "Nex Mail SMTP test"))
    p.add_argument("--imap-host", default=_env("TEST_IMAP_HOST"))
    p.add_argument("--imap-port", type=int, default=int(_env("TEST_IMAP_PORT", "993") or "993"))
    p.add_argument("--imap-user", default=_env("TEST_IMAP_USER"))
    p.add_argument("--imap-password", default=_env("TEST_IMAP_PASSWORD"))
    args = p.parse_args()

    if not args.smtp_user or not args.smtp_password:
        print("Set TEST_SMTP_USER and TEST_SMTP_PASSWORD (or pass --smtp-user / --smtp-password).", file=sys.stderr)
        return 2
    if not args.to:
        print("Set TEST_TO (or pass --to).", file=sys.stderr)
        return 2

    mail_from = args.from_addr or args.smtp_user
    use_tls = not args.no_starttls and args.smtp_port != 25

    print(f"SMTP {args.smtp_host}:{args.smtp_port} STARTTLS={use_tls} user={args.smtp_user!r} -> {args.to!r}")
    try:
        send_smtp(
            args.smtp_host,
            args.smtp_port,
            args.smtp_user,
            args.smtp_password,
            mail_from,
            args.to,
            args.subject,
            use_starttls=use_tls,
        )
    except Exception as exc:
        print(f"SMTP FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print("SMTP OK — message accepted for delivery.")

    imap_host = args.imap_host
    if imap_host:
        iu = args.imap_user or args.smtp_user
        ipw = args.imap_password or args.smtp_password
        print(f"IMAP {imap_host}:{args.imap_port} user={iu!r}")
        try:
            check_imap(imap_host, args.imap_port, iu, ipw)
        except Exception as exc:
            print(f"IMAP FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
