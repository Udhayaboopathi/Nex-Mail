from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import SpamReport

router = APIRouter(tags=["spam_reports"])


class SpamReportRequest(BaseModel):
    mailbox_id: str
    email_uid: str
    from_address: str | None = None
    report_type: str = "spam"


class SpamReportItem(BaseModel):
    id: str
    mailbox_id: str
    email_uid: str
    from_address: str | None
    report_type: str
    created_at: str


@router.get("/", response_model=list[SpamReportItem])
async def list_spam_reports(user: dict = Depends(require_any_auth)) -> list[SpamReportItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(SpamReport).order_by(SpamReport.created_at.desc()))).scalars().all()
    return [
        SpamReportItem(
            id=str(r.id),
            mailbox_id=str(r.mailbox_id),
            email_uid=r.email_uid or "",
            from_address=r.from_address,
            report_type=r.report_type or "spam",
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]


@router.post("/spam")
async def report_spam(payload: SpamReportRequest, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        mailbox_uuid = UUID(payload.mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    async with AsyncSessionLocal() as db:
        report = SpamReport(
            mailbox_id=mailbox_uuid,
            email_uid=payload.email_uid,
            from_address=payload.from_address,
            report_type="spam",
        )
        db.add(report)
        await db.commit()
    return {"ok": True}


@router.post("/not-spam")
async def report_not_spam(payload: SpamReportRequest, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        mailbox_uuid = UUID(payload.mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    async with AsyncSessionLocal() as db:
        report = SpamReport(
            mailbox_id=mailbox_uuid,
            email_uid=payload.email_uid,
            from_address=payload.from_address,
            report_type="ham",
        )
        db.add(report)
        await db.commit()
    return {"ok": True}
