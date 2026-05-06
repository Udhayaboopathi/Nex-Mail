from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import Label

router = APIRouter(tags=["folders"])


class FolderItem(BaseModel):
    name: str
    type: str
    label_id: str | None = None
    color: str | None = None


@router.get("/", response_model=list[FolderItem])
async def list_folders(user: dict = Depends(require_any_auth)) -> list[FolderItem]:
    system_folders = [
        FolderItem(name="Inbox", type="system"),
        FolderItem(name="Sent", type="system"),
        FolderItem(name="Drafts", type="system"),
        FolderItem(name="Starred", type="system"),
        FolderItem(name="Spam", type="system"),
        FolderItem(name="Trash", type="system"),
        FolderItem(name="Archive", type="system"),
    ]
    async with AsyncSessionLocal() as db:
        labels = (await db.execute(select(Label).order_by(Label.name.asc()))).scalars().all()
    label_folders = [
        FolderItem(name=l.name or "", type="label", label_id=str(l.id), color=l.color)
        for l in labels
    ]
    return system_folders + label_folders
