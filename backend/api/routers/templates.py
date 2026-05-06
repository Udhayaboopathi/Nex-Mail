from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import EmailTemplate

router = APIRouter(tags=["templates"])


class TemplateItem(BaseModel):
    id: str
    name: str
    subject: str
    body_html: str | None = None
    body_text: str | None = None
    created_at: str
    updated_at: str


class CreateTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    subject: str = Field(min_length=1)
    mailbox_id: str
    body_html: str | None = None
    body_text: str | None = None


class UpdateTemplateRequest(BaseModel):
    name: str | None = None
    subject: str | None = None
    body_html: str | None = None
    body_text: str | None = None


def _to_item(t: EmailTemplate) -> TemplateItem:
    return TemplateItem(
        id=str(t.id),
        name=t.name or "",
        subject=t.subject or "",
        body_html=t.body_html,
        body_text=t.body_text,
        created_at=t.created_at.isoformat() if t.created_at else "",
        updated_at=t.updated_at.isoformat() if t.updated_at else "",
    )


@router.get("/", response_model=list[TemplateItem])
async def list_templates(user: dict = Depends(require_any_auth)) -> list[TemplateItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(EmailTemplate).order_by(EmailTemplate.created_at.desc()))).scalars().all()
    return [_to_item(t) for t in rows]


@router.post("/", response_model=TemplateItem)
async def create_template(payload: CreateTemplateRequest, user: dict = Depends(require_any_auth)) -> TemplateItem:
    try:
        mailbox_uuid = UUID(payload.mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    async with AsyncSessionLocal() as db:
        tmpl = EmailTemplate(
            mailbox_id=mailbox_uuid,
            name=payload.name,
            subject=payload.subject,
            body_html=payload.body_html,
            body_text=payload.body_text,
        )
        db.add(tmpl)
        await db.commit()
        await db.refresh(tmpl)
    return _to_item(tmpl)


@router.patch("/{template_id}", response_model=TemplateItem)
async def update_template(template_id: str, payload: UpdateTemplateRequest, user: dict = Depends(require_any_auth)) -> TemplateItem:
    try:
        tmpl_uuid = UUID(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid template_id") from exc
    async with AsyncSessionLocal() as db:
        tmpl = (await db.execute(select(EmailTemplate).where(EmailTemplate.id == tmpl_uuid))).scalar_one_or_none()
        if tmpl is None:
            raise HTTPException(status_code=404, detail="Template not found")
        if payload.name is not None:
            tmpl.name = payload.name
        if payload.subject is not None:
            tmpl.subject = payload.subject
        if payload.body_html is not None:
            tmpl.body_html = payload.body_html
        if payload.body_text is not None:
            tmpl.body_text = payload.body_text
        tmpl.updated_at = datetime.now(tz=timezone.utc)
        await db.commit()
        await db.refresh(tmpl)
    return _to_item(tmpl)


@router.delete("/{template_id}")
async def delete_template(template_id: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        tmpl_uuid = UUID(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid template_id") from exc
    async with AsyncSessionLocal() as db:
        tmpl = (await db.execute(select(EmailTemplate).where(EmailTemplate.id == tmpl_uuid))).scalar_one_or_none()
        if tmpl is None:
            raise HTTPException(status_code=404, detail="Template not found")
        await db.delete(tmpl)
        await db.commit()
    return {"ok": True}
