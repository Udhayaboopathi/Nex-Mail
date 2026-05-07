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
    """FQDN for MX / mail A record (domain-scoped, never cross-domain)."""
    mh = (settings.smtp_hostname or "").strip().lower().rstrip(".")
    apex = domain.name.lower().rstrip(".")
    # Only reuse SMTP_HOSTNAME if it belongs to this apex domain.
    if mh and (mh == apex or mh.endswith(f".{apex}")):
        return mh
    return f"mail.{apex}"


def bimi_txt_record_for_domain(domain: Domain) -> str | None:
    logo = (domain.whitelabel_logo_url or "").strip()
    if not logo:
        return None
    vmc = (domain.bimi_vmc_url or "").strip()
    if vmc:
        return f"v=BIMI1; l={logo}; a={vmc};"
    return f"v=BIMI1; l={logo};"


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
    bimi_txt = bimi_txt_record_for_domain(domain)
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
        async def list_records(rtype: str, name: str) -> list[dict]:
            lr = await client.get(api_base, headers=headers, params={"type": rtype, "name": name})
            lr.raise_for_status()
            return lr.json().get("result") or []

        async def delete_record(rid: str, label: str) -> None:
            nonlocal all_ok
            if not rid:
                all_ok = False
                steps.append(f"fail delete {label}: missing record id")
                return
            try:
                dr = await client.delete(f"{api_base}/{rid}", headers=headers)
                ok, err = await _cf_ok(dr)
                if not ok:
                    all_ok = False
                    steps.append(f"fail delete {label}: {err or dr.text}")
                else:
                    steps.append(f"ok delete {label}")
            except Exception as exc:
                all_ok = False
                steps.append(f"fail delete {label}: {exc}")

        async def upsert_simple(rtype: str, name: str, body: dict) -> None:
            nonlocal all_ok
            merged = {"type": rtype, "name": name, "ttl": 300, **body}
            if rtype == "A":
                merged["proxied"] = False
            try:
                rows = await list_records(rtype, name)
                if rows:
                    rid = rows[0]["id"]
                    pr = await client.patch(f"{api_base}/{rid}", headers=headers, json=merged)
                    for extra in rows[1:]:
                        await delete_record(extra.get("id", ""), f"{rtype} {name} duplicate")
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
                rows = await list_records("TXT", apex)
                spf_rows = [r for r in rows if "v=spf1" in (r.get("content") or "")]
                if spf_rows:
                    rid = spf_rows[0]["id"]
                    pr = await client.patch(f"{api_base}/{rid}", headers=headers, json=body)
                    # Keep only one SPF record at apex.
                    for extra in spf_rows[1:]:
                        await delete_record(extra.get("id", ""), f"TXT SPF {apex} duplicate")
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
            # A and CNAME cannot coexist for same host; remove conflicting CNAME first.
            try:
                cname_rows = await list_records("CNAME", mail_host)
                for row in cname_rows:
                    await delete_record(row.get("id", ""), f"CNAME {mail_host} (conflicts with A)")
            except Exception as exc:
                all_ok = False
                steps.append(f"fail cleanup CNAME {mail_host}: {exc}")
            await upsert_simple("A", mail_host, {"content": server_ip})
        else:
            steps.append("skip A (set SERVER_IP in backend .env for automatic mail host A record)")

        async def upsert_mx() -> None:
            nonlocal all_ok
            body = {"type": "MX", "name": apex, "content": mail_host, "priority": 10, "ttl": 300}
            target = mail_host.rstrip(".").lower()
            try:
                rows = await list_records("MX", apex)
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
                # Keep only one MX target for this mail-only domain.
                for extra in rows:
                    if (extra.get("content") or "").rstrip(".").lower() != target:
                        await delete_record(extra.get("id", ""), f"MX {apex} -> {(extra.get('content') or '').strip()}")
                for extra in ours[1:]:
                    await delete_record(extra.get("id", ""), f"MX {apex} duplicate -> {target}")
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
            # Remove invalid wildcard DKIM placeholder that often conflicts.
            try:
                wildcard_name = f"*._domainkey.{apex}"
                wildcard_rows = await list_records("TXT", wildcard_name)
                for r in wildcard_rows:
                    content = (r.get("content") or "").strip().lower()
                    if content in ('"v=dkim1; p="', "v=dkim1; p=", '"v=dkim1; p='):
                        await delete_record(r.get("id", ""), f"TXT {wildcard_name} invalid placeholder")
            except Exception as exc:
                all_ok = False
                steps.append(f"fail cleanup wildcard DKIM {apex}: {exc}")
        else:
            all_ok = False
            steps.append("skip DKIM (no key in DB — recreate domain or restore keys)")

        await upsert_simple("TXT", f"_dmarc.{apex}", {"content": dmarc})
        # Keep only one DMARC record.
        try:
            dmarc_rows = await list_records("TXT", f"_dmarc.{apex}")
            tagged = [r for r in dmarc_rows if "v=dmarc1" in (r.get("content") or "").lower()]
            for extra in tagged[1:]:
                await delete_record(extra.get("id", ""), f"TXT _dmarc.{apex} duplicate")
        except Exception as exc:
            all_ok = False
            steps.append(f"fail cleanup DMARC {apex}: {exc}")

        if bimi_txt:
            await upsert_simple("TXT", f"default._bimi.{apex}", {"content": bimi_txt})

    msg = "Cloudflare DNS sync completed." if all_ok else "Cloudflare DNS sync finished with errors — see steps."
    return {"attempted": True, "ok": all_ok, "message": msg, "steps": steps}


async def remove_cloudflare_mail_dns(zone_id: str, api_token: str, domain: Domain) -> dict[str, object]:
    """Delete mail-only DNS records managed by Nex Mail for a domain."""
    token = api_token.strip()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    api_base = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    steps: list[str] = []
    all_ok = True

    apex = domain.name.lower().rstrip(".")
    mail_host = mail_hostname_for_domain(domain).rstrip(".").lower()
    selector = domain.dkim_selector or settings.dkim_selector
    dkim_fqdn = f"{selector}._domainkey.{apex}"

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
        async def list_records(rtype: str, name: str) -> list[dict]:
            r = await client.get(api_base, headers=headers, params={"type": rtype, "name": name})
            r.raise_for_status()
            return r.json().get("result") or []

        async def delete_record(rid: str, label: str) -> None:
            nonlocal all_ok
            if not rid:
                all_ok = False
                steps.append(f"fail delete {label}: missing record id")
                return
            try:
                dr = await client.delete(f"{api_base}/{rid}", headers=headers)
                ok, err = await _cf_ok(dr)
                if ok:
                    steps.append(f"ok delete {label}")
                else:
                    all_ok = False
                    steps.append(f"fail delete {label}: {err or dr.text}")
            except Exception as exc:
                all_ok = False
                steps.append(f"fail delete {label}: {exc}")

        try:
            mx_rows = await list_records("MX", apex)
            for row in mx_rows:
                target = (row.get("content") or "").rstrip(".").lower()
                if target == mail_host:
                    await delete_record(row.get("id", ""), f"MX {apex} -> {target}")
        except Exception as exc:
            all_ok = False
            steps.append(f"fail list MX {apex}: {exc}")

        try:
            a_rows = await list_records("A", mail_host)
            for row in a_rows:
                await delete_record(row.get("id", ""), f"A {mail_host}")
        except Exception as exc:
            all_ok = False
            steps.append(f"fail list A {mail_host}: {exc}")

        try:
            txt_rows = await list_records("TXT", apex)
            for row in txt_rows:
                content = (row.get("content") or "").lower()
                if "v=spf1" in content:
                    await delete_record(row.get("id", ""), f"TXT SPF {apex}")
        except Exception as exc:
            all_ok = False
            steps.append(f"fail list TXT {apex}: {exc}")

        try:
            dkim_rows = await list_records("TXT", dkim_fqdn)
            for row in dkim_rows:
                await delete_record(row.get("id", ""), f"TXT DKIM {dkim_fqdn}")
        except Exception as exc:
            all_ok = False
            steps.append(f"fail list TXT {dkim_fqdn}: {exc}")

        try:
            dmarc_rows = await list_records("TXT", f"_dmarc.{apex}")
            for row in dmarc_rows:
                content = (row.get("content") or "").lower()
                if "v=dmarc1" in content:
                    await delete_record(row.get("id", ""), f"TXT DMARC _dmarc.{apex}")
        except Exception as exc:
            all_ok = False
            steps.append(f"fail list TXT _dmarc.{apex}: {exc}")

        try:
            bimi_rows = await list_records("TXT", f"default._bimi.{apex}")
            for row in bimi_rows:
                content = (row.get("content") or "").lower()
                if "v=bimi1" in content:
                    await delete_record(row.get("id", ""), f"TXT BIMI default._bimi.{apex}")
        except Exception as exc:
            all_ok = False
            steps.append(f"fail list TXT default._bimi.{apex}: {exc}")

    msg = "Cloudflare mail DNS cleanup completed." if all_ok else "Cloudflare mail DNS cleanup finished with errors."
    return {"attempted": True, "ok": all_ok, "message": msg, "steps": steps}


async def create_domain(
    name: str,
    admin_user_id: str | None = None,
    storage_quota_gb: int | None = None,
) -> dict:
    """Register a new domain and generate its DKIM keypair."""
    quota = 10 if storage_quota_gb is None else max(1, min(int(storage_quota_gb), 2048))
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
            storage_quota_gb=quota,
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


def _txt_rdata_to_unicode(rdata) -> str:
    """Concatenate TXT character-strings in one RR (RFC 6376: no spaces between chunks)."""
    strings = getattr(rdata, "strings", None)
    if not strings:
        return str(rdata)
    parts: list[str] = []
    for s in strings:
        if isinstance(s, bytes):
            parts.append(s.decode("utf-8", errors="replace"))
        else:
            parts.append(str(s))
    return "".join(parts)


def _public_dns_resolver():
    """Avoid stale NXDOMAIN/cache from the container default resolver right after DNS updates."""
    import dns.resolver

    res = dns.resolver.Resolver(configure=False)
    res.nameservers = ["1.1.1.1", "8.8.8.8", "1.0.0.1", "8.8.4.4"]
    res.timeout = 4
    res.lifetime = 12
    return res


def _resolve_txt_strings(resolver, host: str) -> list[str]:
    """One concatenated string per TXT RR at host."""
    answer = resolver.resolve(host, "TXT")
    return [_txt_rdata_to_unicode(r) for r in answer]


async def verify_dns(domain_id: str) -> dict:
    """Check live DNS records for MX, SPF, DKIM, DMARC (queries public resolvers)."""
    res = _public_dns_resolver()

    async with AsyncSessionLocal() as db:
        domain: Domain | None = (
            await db.execute(select(Domain).where(Domain.id == UUID(str(domain_id))))
        ).scalar_one_or_none()
        if not domain:
            raise ValueError("Domain not found.")
        name = domain.name
        selector = domain.dkim_selector or settings.dkim_selector

    results: dict[str, dict] = {}

    # MX
    try:
        mx = res.resolve(name, "MX")
        results["mx"] = {"ok": True, "value": str(sorted(mx, key=lambda r: r.preference)[0].exchange)}
    except Exception as exc:
        results["mx"] = {"ok": False, "error": str(exc)}

    # SPF
    try:
        txt_vals = _resolve_txt_strings(res, name)
        spf = next((t for t in txt_vals if "v=spf1" in t), None)
        results["spf"] = {"ok": bool(spf), "value": spf}
    except Exception as exc:
        results["spf"] = {"ok": False, "error": str(exc)}

    # DKIM
    try:
        dkim_host = f"{selector}._domainkey.{name}"
        txt_vals = _resolve_txt_strings(res, dkim_host)
        dkim_val = next((t for t in txt_vals if "v=DKIM1" in t), (txt_vals[0] if txt_vals else ""))
        results["dkim"] = {"ok": bool(dkim_val and "v=DKIM1" in dkim_val), "value": dkim_val}
    except Exception as exc:
        results["dkim"] = {"ok": False, "error": str(exc)}

    # DMARC
    try:
        txt_vals = _resolve_txt_strings(res, f"_dmarc.{name}")
        dmarc = next((t for t in txt_vals if "v=DMARC1" in t), None)
        results["dmarc"] = {"ok": bool(dmarc), "value": dmarc}
    except Exception as exc:
        results["dmarc"] = {"ok": False, "error": str(exc)}

    all_ok = all(v.get("ok") for v in results.values())

    # Persist verification status
    async with AsyncSessionLocal() as db:
        domain = (
            await db.execute(select(Domain).where(Domain.id == UUID(str(domain_id))))
        ).scalar_one_or_none()
        if domain:
            domain.dns_verified = all_ok
            domain.dns_verified_at = datetime.now(tz=timezone.utc) if all_ok else None
            await db.commit()

    return {
        "domain": name,
        "dkim_selector": selector,
        "all_ok": all_ok,
        "records": results,
    }
