from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.services.branding_service import domain_branding_file_path

router = APIRouter(tags=["public-assets"])


@router.get("/domain-branding/{domain_slug}/{filename}")
async def get_domain_branding_asset(domain_slug: str, filename: str):
    try:
        path = domain_branding_file_path(domain_slug, filename)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Asset not found") from exc
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    media_type = "image/svg+xml" if filename.endswith(".svg") else "application/x-pem-file"
    return FileResponse(Path(path), media_type=media_type)
