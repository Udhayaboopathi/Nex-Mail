from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import Label, Mailbox

router = APIRouter(tags=["mail"])


class FolderItem(BaseModel):
    name: str
    unread: int
    total: int
    color: str | None = None


class FolderListResponse(BaseModel):
    folders: list[FolderItem]


class SearchResultItem(BaseModel):
    uid: str
    subject: str
    from_address: str
    preview: str
    folder: str


class SearchResponse(BaseModel):
    query: str
    items: list[SearchResultItem]


SYSTEM_FOLDERS = ["inbox", "sent", "drafts", "starred", "spam", "trash", "archive"]


@router.get("/folders", response_model=FolderListResponse)
async def list_folders(user: dict = Depends(require_any_auth)) -> FolderListResponse:
    folders: list[FolderItem] = [FolderItem(name=f, unread=0, total=0) for f in SYSTEM_FOLDERS]

    async with AsyncSessionLocal() as db:
        try:
            from backend.models.all_models import Email
            mailbox = (await db.execute(
                select(Mailbox).limit(1)
            )).scalar_one_or_none()

            if mailbox:
                mid = mailbox.id
                for i, fname in enumerate(SYSTEM_FOLDERS):
                    total = int(await db.scalar(
                        select(func.count()).where(
                            Email.mailbox_id == mid,
                            Email.folder == fname,
                        )
                    ) or 0)
                    unread = int(await db.scalar(
                        select(func.count()).where(
                            Email.mailbox_id == mid,
                            Email.folder == fname,
                            Email.is_read == False,
                        )
                    ) or 0)
                    folders[i] = FolderItem(name=fname, unread=unread, total=total)
        except Exception:
            pass

        labels = (await db.execute(select(Label).order_by(Label.name.asc()))).scalars().all()
        for lbl in labels:
            folders.append(FolderItem(name=lbl.name or "", unread=0, total=0, color=lbl.color))

    return FolderListResponse(folders=folders)


@router.get("/search", response_model=SearchResponse)
async def search_mail(
    q: str = Query(default="", min_length=0),
    user: dict = Depends(require_any_auth),
) -> SearchResponse:
    if not q or not q.strip():
        return SearchResponse(query=q, items=[])

    items: list[SearchResultItem] = []
    try:
        from backend.models.all_models import Email
        async with AsyncSessionLocal() as db:
            like = f"%{q.strip()}%"
            rows = (await db.execute(
                select(Email).where(
                    or_(
                        Email.subject.ilike(like),
                        Email.from_address.ilike(like),
                        Email.body_text.ilike(like),
                    )
                ).order_by(Email.sent_at.desc()).limit(25)
            )).scalars().all()
            for e in rows:
                items.append(SearchResultItem(
                    uid=str(e.id),
                    subject=e.subject or "(no subject)",
                    from_address=e.from_address or "",
                    preview=(e.body_text or "")[:120],
                    folder=e.folder or "inbox",
                ))
    except Exception:
        pass

    return SearchResponse(query=q, items=items)
