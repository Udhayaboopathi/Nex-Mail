from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(tags=["mail"])


class FolderItem(BaseModel):
    name: str
    unread: int
    total: int


class FolderListResponse(BaseModel):
    folders: list[FolderItem]


class SearchResultItem(BaseModel):
    uid: str
    subject: str
    from_address: str
    preview: str


class SearchResponse(BaseModel):
    query: str
    items: list[SearchResultItem]


@router.get("/folders", response_model=FolderListResponse)
async def list_folders() -> FolderListResponse:
    return FolderListResponse(
        folders=[
            FolderItem(name="Inbox", unread=0, total=0),
            FolderItem(name="Sent", unread=0, total=0),
            FolderItem(name="Drafts", unread=0, total=0),
            FolderItem(name="Spam", unread=0, total=0),
        ]
    )


@router.get("/search", response_model=SearchResponse)
async def search_mail(q: str = Query(default="", min_length=0)) -> SearchResponse:
    if not q:
        return SearchResponse(query=q, items=[])
    return SearchResponse(
        query=q,
        items=[
            SearchResultItem(
                uid="preview-1",
                subject=f"Search preview for '{q}'",
                from_address="system@localhost",
                preview="Mail indexing is active; full-text hits will appear here.",
            )
        ],
    )
