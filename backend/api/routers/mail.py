from email import message_from_bytes
from email.message import EmailMessage
from email.message import Message
from email.utils import getaddresses
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.imap import maildir
from backend.models import Label, Mailbox
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
    model_config = ConfigDict(populate_by_name=True)

    uid: str
    from_: str = Field(alias="from")
    to: list[str]
    subject: str
    date: str
    is_read: bool
    is_flagged: bool
    has_attachments: bool
    folder: str
    preview: str

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
    # Frontend currently sends to_addresses/cc_addresses/bcc_addresses.
    # Support both the simple "to" field and the structured fields.
    to: list[str] | None = None
    to_addresses: list[str] | None = None
    cc_addresses: list[str] | None = None
    bcc_addresses: list[str] | None = None
    subject: str
    body_text: str = ""
    body_html: str | None = None


SYSTEM_FOLDERS = ["inbox", "sent", "drafts", "starred", "spam", "trash", "archive"]


def _folder_to_maildir_name(folder: str) -> str:
    mapping = {
        "inbox": "INBOX",
        "sent": "Sent",
        "drafts": "Drafts",
        "starred": "Starred",
        "spam": "Spam",
        "trash": "Trash",
        "archive": "Archive",
    }
    return mapping.get(folder, folder)


def _message_preview(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                payload = part.get_payload(decode=True) or b""
                text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                return " ".join(text.strip().split())[:200]
    payload = msg.get_payload(decode=True) or b""
    text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    return " ".join(text.strip().split())[:200]


def _message_has_attachments(msg: Message) -> bool:
    if not msg.is_multipart():
        return False
    return any(part.get_filename() for part in msg.walk())


async def _mailbox_for_user(user: dict) -> Mailbox | None:
    email = (user.get("email") or "").strip().lower()
    if not email:
        return None
    async with AsyncSessionLocal() as db:
        return (await db.execute(
            select(Mailbox).where(Mailbox.full_address == email, Mailbox.is_active == True)
        )).scalar_one_or_none()


def _maildir_candidates(mailbox: Mailbox) -> list[str]:
    local, domain = (mailbox.full_address or "@").split("@", 1)
    candidates: list[str] = []
    if mailbox.maildir_path:
        candidates.append(mailbox.maildir_path)
    # Canonical layout used by mailbox_service.create_mailbox
    candidates.append(str(Path(settings.maildir_base) / domain / local))
    # Legacy fallback layout used by SMTP handler when maildir_path is missing
    candidates.append(str(Path(settings.maildir_base) / f"{local}_{domain}"))
    # Keep order, remove duplicates
    out: list[str] = []
    for p in candidates:
        if p and p not in out:
            out.append(p)
    return out


def _resolve_maildir_path(mailbox: Mailbox) -> str:
    """Pick an existing Maildir path; otherwise return the canonical path."""
    for p in _maildir_candidates(mailbox):
        if Path(p).exists():
            return p
    return _maildir_candidates(mailbox)[0]


@router.get("/folders", response_model=FolderListResponse)
async def list_folders(user: dict = Depends(require_any_auth)) -> FolderListResponse:
    """Return folder list and counts from the user's Maildir."""
    folders: list[FolderItem] = [FolderItem(name=f, unread=0, total=0) for f in SYSTEM_FOLDERS]
    mailbox = await _mailbox_for_user(user)

    if mailbox:
        mailbox_path = _resolve_maildir_path(mailbox)
        for i, fname in enumerate(SYSTEM_FOLDERS):
            entries = maildir.list_messages(mailbox_path, _folder_to_maildir_name(fname))
            unread = sum(1 for item in entries if "S" not in item.get("flags", []))
            folders[i] = FolderItem(name=fname, unread=unread, total=len(entries))

    async with AsyncSessionLocal() as db:
        labels = (await db.execute(select(Label).order_by(Label.name.asc()))).scalars().all()
        for lbl in labels:
            folders.append(FolderItem(name=lbl.name or "", unread=0, total=0, color=lbl.color))

    return FolderListResponse(folders=folders)


@router.get("/search", response_model=SearchResponse)
async def search_mail(
    q: str = Query(default="", min_length=0),
    user: dict = Depends(require_any_auth),
) -> SearchResponse:
    """Search the user's Maildir messages by subject/from/body preview."""
    if not q or not q.strip():
        return SearchResponse(query=q, items=[])
    mailbox = await _mailbox_for_user(user)
    if mailbox is None:
        return SearchResponse(query=q, items=[])
    mailbox_path = _resolve_maildir_path(mailbox)

    needle = q.strip().lower()
    out: list[SearchResultItem] = []
    for fname in SYSTEM_FOLDERS:
        md_folder = _folder_to_maildir_name(fname)
        entries = list(reversed(maildir.list_messages(mailbox_path, md_folder)))
        for item in entries[:100]:
            raw = maildir.read_message(mailbox_path, md_folder, item["uid"])
            if raw is None:
                continue
            msg = message_from_bytes(raw)
            subject = str(msg.get("Subject") or "(no subject)")
            from_addr = str(msg.get("From") or "")
            preview = _message_preview(msg)
            hay = f"{subject}\n{from_addr}\n{preview}".lower()
            if needle in hay:
                out.append(
                    SearchResultItem(
                        uid=item["uid"],
                        subject=subject,
                        from_address=from_addr,
                        preview=preview,
                        folder=fname,
                    )
                )
            if len(out) >= 50:
                return SearchResponse(query=q, items=out)
    return SearchResponse(query=q, items=out)


@router.get("/{folder}", response_model=PaginatedEmailHeaders)
async def list_messages(
    folder: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(require_any_auth),
) -> PaginatedEmailHeaders:
    """List messages from the user's Maildir for the requested folder."""
    if folder not in SYSTEM_FOLDERS:
        raise HTTPException(status_code=404, detail="Folder not found")

    mailbox = await _mailbox_for_user(user)
    if mailbox is None:
        return PaginatedEmailHeaders(items=[], total=0, page=page, limit=limit)
    mailbox_path = _resolve_maildir_path(mailbox)

    md_folder = _folder_to_maildir_name(folder)
    entries = list(reversed(maildir.list_messages(mailbox_path, md_folder)))
    total = len(entries)
    start = (page - 1) * limit
    end = start + limit
    page_items = entries[start:end]

    items: list[EmailHeaderItem] = []
    for item in page_items:
        raw = maildir.read_message(mailbox_path, md_folder, item["uid"])
        if raw is None:
            continue
        msg = message_from_bytes(raw)
        to_list = [addr for _, addr in getaddresses([str(msg.get("To") or "")]) if addr]
        flags = item.get("flags", [])
        items.append(
            EmailHeaderItem(
                uid=item["uid"],
                from_=str(msg.get("From") or ""),
                to=to_list,
                subject=str(msg.get("Subject") or "(no subject)"),
                date=str(msg.get("Date") or ""),
                is_read="S" in flags,
                is_flagged="F" in flags,
                has_attachments=_message_has_attachments(msg),
                folder=folder,
                preview=_message_preview(msg),
            )
        )

    return PaginatedEmailHeaders(items=items, total=total, page=page, limit=limit)


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

    # Normalize recipients from either "to" or "to_addresses".
    to_list = payload.to if payload.to is not None else payload.to_addresses or []
    if not to_list:
        raise HTTPException(status_code=422, detail="At least one recipient is required.")

    result = await smtp_send_email(
        to=to_list,
        subject=payload.subject,
        body_text=payload.body_text,
        body_html=payload.body_html,
        from_addr=sender,
    )
    # Save a local Sent copy so the Sent tab reflects successful sends immediately.
    sender_mailbox = await _mailbox_for_user(user)
    if sender_mailbox:
        mailbox_path = _resolve_maildir_path(sender_mailbox)
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = ", ".join(to_list)
        msg["Subject"] = payload.subject
        msg.set_content(payload.body_text or "")
        if payload.body_html:
            msg.add_alternative(payload.body_html, subtype="html")
        maildir.write_message(mailbox_path, "Sent", msg.as_bytes(), flags="S")
    return {"message_id": result.get("message_id", "")}
