from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.api.deps import require_any_auth
from backend.services.ai_service import rank_mailboxes_by_usage

router = APIRouter(tags=["ai"])


class PriorityMailbox(BaseModel):
    full_address: str
    used_mb: float
    quota_mb: float
    priority_score: float


class PriorityInboxResponse(BaseModel):
    items: list[PriorityMailbox]


class SummarizeRequest(BaseModel):
    thread_id: str


class SummarizeResponse(BaseModel):
    summary: str


class SmartReplyRequest(BaseModel):
    message_id: str


class SmartReplyResponse(BaseModel):
    suggestions: list[str]


class SuggestLabelsRequest(BaseModel):
    message_id: str


class SuggestLabelsResponse(BaseModel):
    labels: list[str]


@router.get("/priority-inbox", response_model=PriorityInboxResponse)
async def get_priority_inbox(user: dict = Depends(require_any_auth)) -> PriorityInboxResponse:
    ranked = await rank_mailboxes_by_usage(limit=20)
    items = [PriorityMailbox(**item) for item in ranked]
    return PriorityInboxResponse(items=items)


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_thread(payload: SummarizeRequest, user: dict = Depends(require_any_auth)) -> SummarizeResponse:
    try:
        from backend.services.ai_service import summarize_thread as _summarize
        summary = await _summarize(payload.thread_id)
    except Exception:
        summary = "AI summarization is not configured."
    return SummarizeResponse(summary=summary)


@router.post("/smart-reply", response_model=SmartReplyResponse)
async def smart_reply(payload: SmartReplyRequest, user: dict = Depends(require_any_auth)) -> SmartReplyResponse:
    try:
        from backend.services.ai_service import smart_reply_suggestions as _smart
        suggestions = await _smart(payload.message_id)
    except Exception:
        suggestions = ["Thank you for your email.", "I will get back to you shortly.", "Could you please provide more details?"]
    return SmartReplyResponse(suggestions=suggestions)


@router.post("/suggest-labels", response_model=SuggestLabelsResponse)
async def suggest_labels(payload: SuggestLabelsRequest, user: dict = Depends(require_any_auth)) -> SuggestLabelsResponse:
    try:
        from backend.services.ai_service import suggest_labels as _suggest
        labels = await _suggest(payload.message_id)
    except Exception:
        labels = []
    return SuggestLabelsResponse(labels=labels)
