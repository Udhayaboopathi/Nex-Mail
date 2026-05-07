from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import Label
from backend.smtp.outbound import send_email as smtp_send_email

router = APIRouter(tags=["mail"])


class FolderItem(BaseModel):
    name: str
    unread: int
    total: int
    color: str | None = None


class FolderListResponse(BaseModel):
    folders: list[FolderItem]


class EmailHeaderItem(BaseModel):
    uid: str
    from_: str
    to: list[str]
    subject: str
    date: str
    is_read: bool
    is_flagged: bool
    has_attachments: bool
    folder: str
    preview: str

    class Config:
        fields = {"from_": "from"}


class PaginatedEmailHeaders(BaseModel):
    items: list[EmailHeaderItem]
    total: int
    page: int
    limit: int


class SearchResultItem(BaseModel):
    uid: str
    subject: str
    from_address: str
    preview: str
    folder: str


class SearchResponse(BaseModel):
    query: str
    items: list[SearchResultItem]


class SendEmailRequest(BaseModel):
    to: list[str]
    subject: str
    body_text: str = ""
    body_html: str | None = None


SYSTEM_FOLDERS = ["inbox", "sent", "drafts", "starred", "spam", "trash", "archive"]


@router.get("/folders", response_model=FolderListResponse)
async def list_folders(user: dict = Depends(require_any_auth)) -> FolderListResponse:
    """Return folder list and counts. Currently returns zero counts plus label folders."""
    folders: list[FolderItem] = [FolderItem(name=f, unread=0, total=0) for f in SYSTEM_FOLDERS]

    async with AsyncSessionLocal() as db:
        labels = (await db.execute(Label.__table__.select().order_by(Label.name.asc()))).scalars().all()
        for lbl in labels:
            folders.append(FolderItem(name=lbl.name or "", unread=0, total=0, color=lbl.color))

    return FolderListResponse(folders=folders)


@router.get("/{folder}", response_model=PaginatedEmailHeaders)
async def list_messages(
    folder: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(require_any_auth),
) -> PaginatedEmailHeaders:
    """Stub message listing so the UI does not 404.

    Real email storage is not wired yet, so we return an empty page structure that
    matches the frontend `Paginated<EmailHeader>` type.
    """
    if folder not in SYSTEM_FOLDERS:
        raise HTTPException(status_code=404, detail="Folder not found")
    return PaginatedEmailHeaders(items=[], total=0, page=page, limit=limit)


@router.get("/search", response_model=SearchResponse)
async def search_mail(
    q: str = Query(default="", min_length=0),
    user: dict = Depends(require_any_auth),
) -> SearchResponse:
    """Stub search endpoint — returns no results for now."""
    if not q or not q.strip():
        return SearchResponse(query=q, items=[])
    return SearchResponse(query=q, items=[])


@router.post("/send")
async def send_email(
    payload: SendEmailRequest,
    user: dict = Depends(require_any_auth),
) -> dict:
    """Send an email for the authenticated user.

    This wires the compose UI's POST /api/mail/send to the SMTP delivery helper.
    """
    sender = user.get("email") or user.get("username") or ""
    if not sender:
        raise HTTPException(status_code=400, detail="Sender address not available for this user")

    result = await smtp_send_email(
        to=payload.to,
        subject=payload.subject,
        body_text=payload.body_text,
        body_html=payload.body_html,
        from_addr=sender,
    )
    return {"message_id": result.get("message_id", "")}
