"""
SMTP server startup.

TLS certificates are loaded from /etc/ssl/mail/ (Let's Encrypt via Certbot).
If the certificates are not present yet (first boot before Certbot has run),
a self-signed certificate is generated automatically so the server can start.
Replace with real certs by running: certbot certonly --webroot ...
"""
from __future__ import annotations

import datetime
import ipaddress
import os
import ssl
import tempfile

from aiosmtpd.controller import Controller

from backend.smtp.handler import InboundHandler, SubmissionHandler

CERT_PATH = "/etc/ssl/mail/fullchain.pem"
KEY_PATH  = "/etc/ssl/mail/privkey.pem"


def _generate_self_signed(hostname: str = "mail.localhost") -> tuple[str, str]:
    """
    Generate a temporary self-signed RSA cert and return (cert_path, key_path).
    Files are written to a stable location so they survive container restarts
    within the same run, but are never committed to the image.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    tmp_dir = "/tmp/smtp-selfsigned"
    os.makedirs(tmp_dir, exist_ok=True)
    cert_file = os.path.join(tmp_dir, "fullchain.pem")
    key_file  = os.path.join(tmp_dir, "privkey.pem")

    # Re-use existing self-signed cert if already generated
    if os.path.exists(cert_file) and os.path.exists(key_file):
        return cert_file, key_file

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(hostname)]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    return cert_file, key_file


def _submission_auth_callback(_mechanism: str, _login: bytes, _password: bytes) -> bool:
    """Accept any credentials until real mailbox auth is implemented for port 587."""
    return True


def _build_tls_context() -> ssl.SSLContext:
    """
    Return an SSLContext loaded with real Let's Encrypt certs if available,
    otherwise fall back to a self-signed certificate so startup never fails.
    """
    if os.path.exists(CERT_PATH) and os.path.exists(KEY_PATH):
        cert_file, key_file = CERT_PATH, KEY_PATH
    else:
        from backend.config import settings
        hostname = getattr(settings, "smtp_hostname", "mail.localhost")
        print(
            f"[SMTP] WARNING: TLS certs not found at {CERT_PATH}. "
            "Using self-signed certificate. Run Certbot to obtain real certs."
        )
        cert_file, key_file = _generate_self_signed(hostname)

    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(cert_file, key_file)
    return ctx


async def create_smtp_servers():
    tls_ctx = _build_tls_context()

    # Port 25  — inbound MTA (no auth, no forced TLS)
    c1 = Controller(InboundHandler(), hostname="0.0.0.0", port=25)

    # Port 587 — submission (authenticated clients, STARTTLS required)
    c2 = Controller(
        SubmissionHandler(),
        hostname="0.0.0.0",
        port=587,
        require_starttls=True,
        tls_context=tls_ctx,
        auth_required=True,
        auth_require_tls=True,
        auth_callback=_submission_auth_callback,
    )

    c1.start()
    c2.start()
    return c1, c2
