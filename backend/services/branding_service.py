from __future__ import annotations

import base64
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


def _ensure_svg_bytes(filename: str, content_type: str, data: bytes) -> bytes:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    is_svg = ("svg" in ctype) or name.endswith(".svg")
    if is_svg:
        return data

    mime = ""
    if "png" in ctype or name.endswith(".png"):
        mime = "image/png"
    elif "jpeg" in ctype or "jpg" in ctype or name.endswith(".jpg") or name.endswith(".jpeg"):
        mime = "image/jpeg"
    elif "webp" in ctype or name.endswith(".webp"):
        mime = "image/webp"
    elif "gif" in ctype or name.endswith(".gif"):
        mime = "image/gif"
    elif "bmp" in ctype or name.endswith(".bmp"):
        mime = "image/bmp"
    if not mime:
        raise ValueError("Unsupported logo format. Use SVG, PNG, JPG, WEBP, GIF, or BMP.")

    b64 = base64.b64encode(data).decode("ascii")
    # Converts raster uploads to a valid SVG wrapper for BIMI URL hosting.
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'>"
        f"<image href='data:{mime};base64,{b64}' width='512' height='512' preserveAspectRatio='xMidYMid meet'/>"
        "</svg>"
    )
    return svg.encode("utf-8")


def domain_branding_file_path(domain_name: str, filename: str) -> Path:
    safe_name = filename.strip().lower()
    if safe_name not in {"bimi-logo.svg", "vmc.pem"}:
        raise ValueError("Unsupported branding asset")
    return Path(settings.domain_branding_storage_dir) / _domain_slug(domain_name) / safe_name


async def save_domain_logo(domain_name: str, upload: UploadFile) -> str:
    content_type = upload.content_type or ""
    filename = upload.filename or ""
    data = await upload.read()
    if not data:
        raise ValueError("Uploaded logo file is empty.")
    if len(data) > 1024 * 1024:
        raise ValueError("Logo file too large (max 1 MB).")
    svg_data = _ensure_svg_bytes(filename, content_type, data)

    domain_dir = Path(settings.domain_branding_storage_dir) / _domain_slug(domain_name)
    domain_dir.mkdir(parents=True, exist_ok=True)
    logo_path = domain_dir / "bimi-logo.svg"
    logo_path.write_bytes(svg_data)
    return f"{_public_base()}/api/public/domain-branding/{_domain_slug(domain_name)}/bimi-logo.svg"


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
    return f"{_public_base()}/api/public/domain-branding/{_domain_slug(domain_name)}/vmc.pem"
