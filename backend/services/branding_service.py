from __future__ import annotations

import re
from pathlib import Path

from fastapi import UploadFile

from backend.config import settings


def _domain_slug(domain_name: str) -> str:
    return re.sub(r"[^a-z0-9.-]+", "-", domain_name.lower()).strip("-")


def _public_base() -> str:
    base = (settings.domain_branding_public_base_url or "").strip().rstrip("/")
    if base:
        return base
    return settings.frontend_url.rstrip("/")


async def save_domain_logo(domain_name: str, upload: UploadFile) -> str:
    content_type = (upload.content_type or "").lower()
    filename = (upload.filename or "").lower()
    if "svg" not in content_type and not filename.endswith(".svg"):
        raise ValueError("Only SVG logos are supported for BIMI.")
    data = await upload.read()
    if not data:
        raise ValueError("Uploaded logo file is empty.")
    if len(data) > 1024 * 1024:
        raise ValueError("Logo file too large (max 1 MB).")

    domain_dir = Path(settings.domain_branding_storage_dir) / _domain_slug(domain_name)
    domain_dir.mkdir(parents=True, exist_ok=True)
    logo_path = domain_dir / "bimi-logo.svg"
    logo_path.write_bytes(data)
    return f"{_public_base()}/static/domain-branding/{_domain_slug(domain_name)}/bimi-logo.svg"


async def save_domain_vmc(domain_name: str, upload: UploadFile) -> str:
    filename = (upload.filename or "").lower()
    content_type = (upload.content_type or "").lower()
    if not (filename.endswith(".pem") or filename.endswith(".crt") or "pem" in content_type or "x-x509" in content_type):
        raise ValueError("VMC file must be a PEM/CRT certificate.")
    data = await upload.read()
    if not data:
        raise ValueError("Uploaded VMC file is empty.")
    if len(data) > 5 * 1024 * 1024:
        raise ValueError("VMC file too large (max 5 MB).")

    domain_dir = Path(settings.domain_branding_storage_dir) / _domain_slug(domain_name)
    domain_dir.mkdir(parents=True, exist_ok=True)
    vmc_path = domain_dir / "vmc.pem"
    vmc_path.write_bytes(data)
    return f"{_public_base()}/static/domain-branding/{_domain_slug(domain_name)}/vmc.pem"
