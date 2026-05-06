"""Domain management service — add, suspend, DNS verification, DKIM keygen."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from sqlalchemy import select

from backend.config import settings
from backend.core.encryption import decrypt_value, encrypt_value
from backend.database import AsyncSessionLocal
from backend.models.all_models import Domain, User

logger = logging.getLogger(__name__)


def build_dkim_txt_record(domain: Domain) -> str | None:
    """Return the full DKIM TXT value (v=DKIM1; k=rsa; p=...) for DNS, or None if no key."""
    if not domain.dkim_private_key_encrypted:
        return None
    try:
        private_pem = decrypt_value(domain.dkim_private_key_encrypted).encode()
        private_key = load_pem_private_key(private_pem, password=None)
        public_pem = (
            private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode()
        )
        b64 = "".join(public_pem.splitlines()[1:-1])
        return f"v=DKIM1; k=rsa; p={b64}"
    except Exception as exc:
        logger.warning("Could not build DKIM TXT for domain %s: %s", domain.name, exc)
        return None


def dkim_txt_dns_name(domain: Domain) -> str:
    """Relative DNS name under the apex zone, e.g. mail._domainkey for selector mail."""
    sel = domain.dkim_selector or settings.dkim_selector
    return f"{sel}._domainkey"


async def fetch_cloudflare_zone_id(api_token: str, domain_name: str) -> str | None:
    """Resolve Cloudflare zone id for an apex domain; returns None if the API call fails."""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(
                "https://api.cloudflare.com/client/v4/zones",
                params={"name": domain_name.lower().strip(), "status": "active"},
                headers={
                    "Authorization": f"Bearer {api_token.strip()}",
                    "Content-Type": "application/json",
                },
            )
            if r.status_code != 200:
                return None
            data = r.json()
            rows = data.get("result") or []
            if not rows:
                return None
            zid = rows[0].get("id")
            return str(zid) if zid else None
    except Exception as exc:
        logger.warning("Cloudflare zone lookup failed for %s: %s", domain_name, exc)
        return None


async def create_domain(name: str, admin_user_id: str | None = None) -> dict:
    """Register a new domain and generate its DKIM keypair."""
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(Domain.id).where(Domain.name == name.lower()))
        if existing:
            raise ValueError(f"Domain '{name}' already exists.")

        # Generate 2048-bit RSA keypair for DKIM
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        # Strip PEM headers and whitespace for the DNS TXT record
        dkim_public_b64 = "".join(public_pem.splitlines()[1:-1])

        domain = Domain(
            name=name.lower(),
            dkim_private_key_encrypted=encrypt_value(private_pem),
            dkim_selector=settings.dkim_selector,
            spf_record=f"v=spf1 mx a:{name.lower()} ~all",
            dmarc_record=f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{name.lower()}",
        )
        if admin_user_id:
            domain.admin_user_id = admin_user_id  # type: ignore[assignment]

        db.add(domain)
        await db.commit()
        await db.refresh(domain)

    return {
        "id": str(domain.id),
        "name": domain.name,
        "dkim_selector": domain.dkim_selector,
        "dkim_public_key": dkim_public_b64,
        "spf_record": domain.spf_record,
        "dmarc_record": domain.dmarc_record,
    }


async def suspend_domain(domain_id: str, reason: str = "") -> None:
    async with AsyncSessionLocal() as db:
        domain: Domain | None = (
            await db.execute(select(Domain).where(Domain.id == domain_id))
        ).scalar_one_or_none()
        if not domain:
            raise ValueError("Domain not found.")
        domain.is_suspended = True
        domain.suspended_at = datetime.now(tz=timezone.utc)
        domain.suspended_reason = reason
        await db.commit()


async def unsuspend_domain(domain_id: str) -> None:
    async with AsyncSessionLocal() as db:
        domain: Domain | None = (
            await db.execute(select(Domain).where(Domain.id == domain_id))
        ).scalar_one_or_none()
        if not domain:
            raise ValueError("Domain not found.")
        domain.is_suspended = False
        domain.suspended_at = None
        domain.suspended_reason = None
        await db.commit()


async def verify_dns(domain_id: str) -> dict:
    """Check live DNS records for MX, SPF, DKIM, DMARC."""
    import dns.resolver

    async with AsyncSessionLocal() as db:
        domain: Domain | None = (
            await db.execute(select(Domain).where(Domain.id == domain_id))
        ).scalar_one_or_none()
        if not domain:
            raise ValueError("Domain not found.")
        name = domain.name
        selector = domain.dkim_selector or settings.dkim_selector

    results: dict[str, dict] = {}

    # MX
    try:
        mx = dns.resolver.resolve(name, "MX")
        results["mx"] = {"ok": True, "value": str(sorted(mx, key=lambda r: r.preference)[0].exchange)}
    except Exception as exc:
        results["mx"] = {"ok": False, "error": str(exc)}

    # SPF
    try:
        txts = dns.resolver.resolve(name, "TXT")
        spf = next((str(r) for r in txts if "v=spf1" in str(r)), None)
        results["spf"] = {"ok": bool(spf), "value": spf}
    except Exception as exc:
        results["spf"] = {"ok": False, "error": str(exc)}

    # DKIM
    try:
        dkim_host = f"{selector}._domainkey.{name}"
        txts = dns.resolver.resolve(dkim_host, "TXT")
        dkim_val = " ".join(str(r) for r in txts)
        results["dkim"] = {"ok": "v=DKIM1" in dkim_val, "value": dkim_val}
    except Exception as exc:
        results["dkim"] = {"ok": False, "error": str(exc)}

    # DMARC
    try:
        txts = dns.resolver.resolve(f"_dmarc.{name}", "TXT")
        dmarc = next((str(r) for r in txts if "v=DMARC1" in str(r)), None)
        results["dmarc"] = {"ok": bool(dmarc), "value": dmarc}
    except Exception as exc:
        results["dmarc"] = {"ok": False, "error": str(exc)}

    all_ok = all(v.get("ok") for v in results.values())

    # Persist verification status
    async with AsyncSessionLocal() as db:
        domain = (
            await db.execute(select(Domain).where(Domain.id == domain_id))
        ).scalar_one_or_none()
        if domain:
            domain.dns_verified = all_ok
            domain.dns_verified_at = datetime.now(tz=timezone.utc) if all_ok else None
            await db.commit()

    return {"domain": name, "all_ok": all_ok, "records": results}
