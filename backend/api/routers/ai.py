from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.ai_service import rank_mailboxes_by_usage

router = APIRouter(tags=["ai"])


class PriorityMailbox(BaseModel):
    full_address: str
    used_mb: float
    quota_mb: float
    priority_score: float


class PriorityInboxResponse(BaseModel):
    items: list[PriorityMailbox]


@router.get("/priority-inbox", response_model=PriorityInboxResponse)
async def get_priority_inbox() -> PriorityInboxResponse:
    ranked = await rank_mailboxes_by_usage(limit=20)
    items = [PriorityMailbox(**item) for item in ranked]
    return PriorityInboxResponse(items=items)
