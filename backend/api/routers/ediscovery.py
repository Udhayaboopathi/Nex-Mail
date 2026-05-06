from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from backend.api.deps import require_domain_admin
from backend.database import AsyncSessionLocal
from backend.models import EdiscoveryExport

router = APIRouter(tags=["ediscovery"])


class EdiscoverySearchRequest(BaseModel):
    domain_id: str
    query: dict = {}


class EdiscoveryExportRequest(BaseModel):
    domain_id: str
    query: dict = {}


class ExportItem(BaseModel):
    id: str
    domain_id: str
    status: str
    total_messages: int
    created_at: str
    completed_at: str | None = None


@router.post("/search")
async def search_ediscovery(payload: EdiscoverySearchRequest, user: dict = Depends(require_domain_admin)) -> dict:
    return {"results": [], "total": 0, "query": payload.query}


@router.post("/export")
async def export_ediscovery(payload: EdiscoveryExportRequest, user: dict = Depends(require_domain_admin)) -> dict[str, str]:
    try:
        domain_uuid = UUID(payload.domain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid domain_id") from exc
    async with AsyncSessionLocal() as db:
        export = EdiscoveryExport(domain_id=domain_uuid, query=payload.query, status="pending", total_messages=0)
        db.add(export)
        await db.commit()
        await db.refresh(export)
    return {"export_id": str(export.id), "status": "pending"}


@router.get("/exports", response_model=list[ExportItem])
async def list_exports(user: dict = Depends(require_domain_admin)) -> list[ExportItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(EdiscoveryExport).order_by(EdiscoveryExport.created_at.desc()))).scalars().all()
    return [
        ExportItem(
            id=str(e.id),
            domain_id=str(e.domain_id),
            status=e.status or "pending",
            total_messages=int(e.total_messages or 0),
            created_at=e.created_at.isoformat() if e.created_at else "",
            completed_at=e.completed_at.isoformat() if e.completed_at else None,
        )
        for e in rows
    ]


@router.get("/exports/{export_id}/download")
async def download_export(export_id: str, user: dict = Depends(require_domain_admin)) -> dict:
    raise HTTPException(status_code=404, detail="Export not ready or not found")
