from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import EmailRule

router = APIRouter(tags=["rules"])


class RuleCondition(BaseModel):
    field: str
    op: str
    value: str = ""


class RuleAction(BaseModel):
    action: str
    value: str | None = None


class RuleItem(BaseModel):
    id: str
    name: str
    is_active: bool
    priority: int
    match_type: str
    conditions: list[RuleCondition]
    actions: list[RuleAction]
    created_at: str


class CreateRuleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    mailbox_id: str
    is_active: bool = True
    priority: int = 0
    match_type: str = "any"
    conditions: list[RuleCondition] = []
    actions: list[RuleAction] = []


class UpdateRuleRequest(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    priority: int | None = None
    match_type: str | None = None
    conditions: list[RuleCondition] | None = None
    actions: list[RuleAction] | None = None


def _to_item(r: EmailRule) -> RuleItem:
    conds = r.conditions if isinstance(r.conditions, list) else []
    acts = r.actions if isinstance(r.actions, list) else []
    return RuleItem(
        id=str(r.id),
        name=r.name or "",
        is_active=bool(r.is_active),
        priority=int(r.priority or 0),
        match_type=r.match_type or "any",
        conditions=[RuleCondition(**c) if isinstance(c, dict) else c for c in conds],
        actions=[RuleAction(**a) if isinstance(a, dict) else a for a in acts],
        created_at=r.created_at.isoformat() if r.created_at else "",
    )


@router.get("/", response_model=list[RuleItem])
async def list_rules(user: dict = Depends(require_any_auth)) -> list[RuleItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(EmailRule).order_by(EmailRule.priority.asc()))).scalars().all()
    return [_to_item(r) for r in rows]


@router.post("/", response_model=RuleItem)
async def create_rule(payload: CreateRuleRequest, user: dict = Depends(require_any_auth)) -> RuleItem:
    try:
        mailbox_uuid = UUID(payload.mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    async with AsyncSessionLocal() as db:
        rule = EmailRule(
            mailbox_id=mailbox_uuid,
            name=payload.name,
            is_active=payload.is_active,
            priority=payload.priority,
            match_type=payload.match_type,
            conditions=[c.model_dump() for c in payload.conditions],
            actions=[a.model_dump() for a in payload.actions],
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
    return _to_item(rule)


@router.patch("/{rule_id}", response_model=RuleItem)
async def update_rule(rule_id: str, payload: UpdateRuleRequest, user: dict = Depends(require_any_auth)) -> RuleItem:
    try:
        rule_uuid = UUID(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid rule_id") from exc
    async with AsyncSessionLocal() as db:
        rule = (await db.execute(select(EmailRule).where(EmailRule.id == rule_uuid))).scalar_one_or_none()
        if rule is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        if payload.name is not None:
            rule.name = payload.name
        if payload.is_active is not None:
            rule.is_active = payload.is_active
        if payload.priority is not None:
            rule.priority = payload.priority
        if payload.match_type is not None:
            rule.match_type = payload.match_type
        if payload.conditions is not None:
            rule.conditions = [c.model_dump() for c in payload.conditions]
        if payload.actions is not None:
            rule.actions = [a.model_dump() for a in payload.actions]
        await db.commit()
        await db.refresh(rule)
    return _to_item(rule)


@router.delete("/{rule_id}")
async def delete_rule(rule_id: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        rule_uuid = UUID(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid rule_id") from exc
    async with AsyncSessionLocal() as db:
        rule = (await db.execute(select(EmailRule).where(EmailRule.id == rule_uuid))).scalar_one_or_none()
        if rule is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        await db.delete(rule)
        await db.commit()
    return {"ok": True}


@router.post("/{rule_id}/test")
async def test_rule(rule_id: str, user: dict = Depends(require_any_auth)) -> dict:
    return {"matched": False, "reason": "Test not implemented for current message"}
