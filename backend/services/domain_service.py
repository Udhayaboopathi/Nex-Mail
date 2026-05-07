"""Domain management service — add, suspend, DNS verification, DKIM keygen."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID

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


def mail_hostname_for_domain(domain: Domain) -> str:
    """FQDN for MX / mail A record (SMTP_HOSTNAME or mail.<apex>)."""
    mh = (settings.smtp_hostname or "").strip().lower().rstrip(".")
    if mh:
        return mh
    return f"mail.{domain.name.lower().rstrip('.')}"


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


async def sync_cloudflare_mail_dns(zone_id: str, api_token: str, domain_id: str) -> dict[str, object]:
    """
    Create or update MX, A (mail host), SPF, DKIM, and DMARC in Cloudflare.
    Requires a token with Zone:DNS:Edit. A record is skipped if SERVER_IP is unset.
    """
    token = api_token.strip()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    api_base = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    steps: list[str] = []
    all_ok = True

    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).where(Domain.id == UUID(domain_id)))).scalar_one_or_none()
        if domain is None:
            return {"attempted": True, "ok": False, "message": "Domain not found", "steps": []}

    apex = domain.name.lower().rstrip(".")
    mail_host = mail_hostname_for_domain(domain)
    server_ip = (settings.server_ip or "").strip()
    selector = domain.dkim_selector or settings.dkim_selector
    dkim_fqdn = f"{selector}._domainkey.{apex}"
    dkim_txt = build_dkim_txt_record(domain)
    spf = (domain.spf_record or f"v=spf1 mx a:{mail_host} ~all").strip()
    dmarc = (domain.dmarc_record or f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{apex}").strip()

    async def _cf_ok(resp: httpx.Response) -> tuple[bool, str]:
        try:
            data = resp.json()
        except Exception:
            return False, resp.text or f"HTTP {resp.status_code}"
        if data.get("success"):
            return True, ""
        errs = data.get("errors") or [{}]
        return False, str(errs[0].get("message") or errs)

    async with httpx.AsyncClient(timeout=45.0) as client:
        async def upsert_simple(rtype: str, name: str, body: dict) -> None:
            nonlocal all_ok
            merged = {"type": rtype, "name": name, "ttl": 300, **body}
            if rtype == "A":
                merged["proxied"] = False
            try:
                lr = await client.get(api_base, headers=headers, params={"type": rtype, "name": name})
                lr.raise_for_status()
                rows = lr.json().get("result") or []
                if rows:
                    rid = rows[0]["id"]
                    pr = await client.patch(f"{api_base}/{rid}", headers=headers, json=merged)
                else:
                    pr = await client.post(api_base, headers=headers, json=merged)
                ok, err = await _cf_ok(pr)
                if not ok:
                    all_ok = False
                    steps.append(f"fail {rtype} {name}: {err or pr.text}")
                else:
                    steps.append(f"ok {rtype} {name}")
            except Exception as exc:
                all_ok = False
                steps.append(f"fail {rtype} {name}: {exc}")

        async def upsert_spf() -> None:
            nonlocal all_ok
            body = {"type": "TXT", "name": apex, "content": spf, "ttl": 300}
            try:
                lr = await client.get(api_base, headers=headers, params={"type": "TXT", "name": apex})
                lr.raise_for_status()
                rows = lr.json().get("result") or []
                spf_rows = [r for r in rows if "v=spf1" in (r.get("content") or "")]
                if spf_rows:
                    rid = spf_rows[0]["id"]
                    pr = await client.patch(f"{api_base}/{rid}", headers=headers, json=body)
                else:
                    pr = await client.post(api_base, headers=headers, json=body)
                ok, err = await _cf_ok(pr)
                if not ok:
                    all_ok = False
                    steps.append(f"fail TXT SPF {apex}: {err or pr.text}")
                else:
                    steps.append(f"ok TXT SPF {apex}")
            except Exception as exc:
                all_ok = False
                steps.append(f"fail TXT SPF {apex}: {exc}")

        if server_ip:
            await upsert_simple("A", mail_host, {"content": server_ip})
        else:
            steps.append("skip A (set SERVER_IP in backend .env for automatic mail host A record)")

        async def upsert_mx() -> None:
            nonlocal all_ok
            body = {"type": "MX", "name": apex, "content": mail_host, "priority": 10, "ttl": 300}
            target = mail_host.rstrip(".").lower()
            try:
                lr = await client.get(api_base, headers=headers, params={"type": "MX", "name": apex})
                lr.raise_for_status()
                rows = lr.json().get("result") or []
                ours = [
                    r
                    for r in rows
                    if (r.get("content") or "").rstrip(".").lower() == target
                ]
                if ours:
                    rid = ours[0]["id"]
                    pr = await client.patch(f"{api_base}/{rid}", headers=headers, json=body)
                else:
                    pr = await client.post(api_base, headers=headers, json=body)
                ok, err = await _cf_ok(pr)
                if not ok:
                    all_ok = False
                    steps.append(f"fail MX {apex}: {err or pr.text}")
                else:
                    steps.append(f"ok MX {apex} -> {mail_host}")
            except Exception as exc:
                all_ok = False
                steps.append(f"fail MX {apex}: {exc}")

        await upsert_mx()
        await upsert_spf()

        if dkim_txt:
            await upsert_simple("TXT", dkim_fqdn, {"content": dkim_txt})
        else:
            all_ok = False
            steps.append("skip DKIM (no key in DB — recreate domain or restore keys)")

        await upsert_simple("TXT", f"_dmarc.{apex}", {"content": dmarc})

    msg = "Cloudflare DNS sync completed." if all_ok else "Cloudflare DNS sync finished with errors — see steps."
    return {"attempted": True, "ok": all_ok, "message": msg, "steps": steps}


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
            spf_record=f"v=spf1 mx a:mail.{name.lower()} ~all",
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
