from email import message_from_bytes
from email.message import Message
from email.utils import getaddresses
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select

from backend.api.deps import require_any_auth
from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.imap import maildir
from backend.models import Email, Label, Mailbox
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


class EmailFullItem(EmailHeaderItem):
    body_html: str | None = None
    body_text: str | None = None
    cc: list[str] = []
    bcc: list[str] = []
    reply_to: str | None = None
    message_id: str = ""
    attachments: list[dict] = []
    read_receipt_token: str | None = None
    is_pgp_encrypted: bool = False


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


def _extract_body(msg: Message) -> tuple[str | None, str | None]:
    body_text: str | None = None
    body_html: str | None = None
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_filename():
                continue
            ctype = part.get_content_type()
            payload = part.get_payload(decode=True) or b""
            text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            if ctype == "text/plain" and body_text is None:
                body_text = text
            elif ctype == "text/html" and body_html is None:
                body_html = text
    else:
        payload = msg.get_payload(decode=True) or b""
        text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
        if msg.get_content_type() == "text/html":
            body_html = text
        else:
            body_text = text
    return body_text, body_html


async def _mailbox_for_user(user: dict) -> Mailbox | None:
    email = (user.get("email") or "").strip().lower()
    user_id = (user.get("id") or "").strip()
    async with AsyncSessionLocal() as db:
        if email:
            mailbox = (await db.execute(
                select(Mailbox).where(Mailbox.full_address == email, Mailbox.is_active == True)
            )).scalar_one_or_none()
            if mailbox is not None:
                return mailbox
        if user_id:
            return (await db.execute(
                select(Mailbox).where(Mailbox.user_id == user_id, Mailbox.is_active == True)
            )).scalar_one_or_none()
        return None


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
        async with AsyncSessionLocal() as db:
            counts = (
                await db.execute(
                    select(Email.folder, func.count())
                    .where(Email.mailbox_id == mailbox.id)
                    .group_by(Email.folder)
                )
            ).all()
            unread_counts = (
                await db.execute(
                    select(Email.folder, func.count())
                    .where(Email.mailbox_id == mailbox.id, Email.is_read == False)
                    .group_by(Email.folder)
                )
            ).all()
        count_map = {str(folder).lower(): int(total) for folder, total in counts}
        unread_map = {str(folder).lower(): int(total) for folder, total in unread_counts}
        for i, fname in enumerate(SYSTEM_FOLDERS):
            folders[i] = FolderItem(
                name=fname,
                unread=unread_map.get(fname, 0),
                total=count_map.get(fname, 0),
            )

    if mailbox:
        async with AsyncSessionLocal() as db:
            labels = (await db.execute(
                select(Label).where(Label.mailbox_id == mailbox.id).order_by(Label.name.asc())
            )).scalars().all()
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
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(Email)
                .where(
                    Email.mailbox_id == mailbox.id,
                    or_(
                        Email.subject.ilike(f"%{q.strip()}%"),
                        Email.from_address.ilike(f"%{q.strip()}%"),
                        Email.body_text.ilike(f"%{q.strip()}%"),
                    ),
                )
                .order_by(Email.created_at.desc())
                .limit(50)
            )
        ).scalars().all()
    if rows:
        return SearchResponse(
            query=q,
            items=[
                SearchResultItem(
                    uid=str(e.id),
                    subject=str(e.subject or "(no subject)"),
                    from_address=str(e.from_address or ""),
                    preview=(" ".join((e.body_text or "").strip().split())[:200]),
                    folder=str(e.folder or "inbox"),
                )
                for e in rows
            ],
        )

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
    async with AsyncSessionLocal() as db:
        total = int(
            await db.scalar(
                select(func.count())
                .where(Email.mailbox_id == mailbox.id, Email.folder == folder)
            )
            or 0
        )
        rows = (
            await db.execute(
                select(Email)
                .where(Email.mailbox_id == mailbox.id, Email.folder == folder)
                .order_by(Email.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
        ).scalars().all()
    if rows:
        return PaginatedEmailHeaders(
            items=[
                EmailHeaderItem(
                    uid=str(e.id),
                    from_=str(e.from_address or ""),
                    to=list(e.to_addresses or []),
                    subject=str(e.subject or "(no subject)"),
                    date=(e.sent_at or e.created_at).isoformat() if (e.sent_at or e.created_at) else "",
                    is_read=bool(e.is_read),
                    is_flagged=bool(e.is_flagged),
                    has_attachments=bool(e.has_attachments),
                    folder=str(e.folder or folder),
                    preview=(" ".join((e.body_text or "").strip().split())[:200]),
                )
                for e in rows
            ],
            total=total,
            page=page,
            limit=limit,
        )
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


@router.get("/{folder}/{uid}", response_model=EmailFullItem)
async def get_message(
    folder: str,
    uid: str,
    user: dict = Depends(require_any_auth),
) -> EmailFullItem:
    if folder not in SYSTEM_FOLDERS:
        raise HTTPException(status_code=404, detail="Folder not found")

    mailbox = await _mailbox_for_user(user)
    if mailbox is None:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    db_uid = None
    try:
        db_uid = UUID(uid)
    except ValueError:
        db_uid = None
    async with AsyncSessionLocal() as db:
        db_msg = None
        if db_uid is not None:
            db_msg = (
                await db.execute(
                    select(Email).where(
                        Email.id == db_uid,
                        Email.mailbox_id == mailbox.id,
                        Email.folder == folder,
                    )
                )
            ).scalar_one_or_none()
    if db_msg is not None:
        return EmailFullItem(
            uid=str(db_msg.id),
            from_=str(db_msg.from_address or ""),
            to=list(db_msg.to_addresses or []),
            subject=str(db_msg.subject or "(no subject)"),
            date=(db_msg.sent_at or db_msg.created_at).isoformat() if (db_msg.sent_at or db_msg.created_at) else "",
            is_read=bool(db_msg.is_read),
            is_flagged=bool(db_msg.is_flagged),
            has_attachments=bool(db_msg.has_attachments),
            folder=str(db_msg.folder or folder),
            preview=(" ".join((db_msg.body_text or "").strip().split())[:200]),
            body_text=db_msg.body_text,
            body_html=db_msg.body_html,
            cc=list(db_msg.cc_addresses or []),
            bcc=list(db_msg.bcc_addresses or []),
            reply_to=None,
            message_id=str(db_msg.message_id or db_msg.id),
            attachments=[],
            read_receipt_token=None,
            is_pgp_encrypted=False,
        )
    mailbox_path = _resolve_maildir_path(mailbox)

    md_folder = _folder_to_maildir_name(folder)
    raw = maildir.read_message(mailbox_path, md_folder, uid)
    if raw is None:
        raise HTTPException(status_code=404, detail="Message not found")

    msg = message_from_bytes(raw)
    flags = []
    for item in maildir.list_messages(mailbox_path, md_folder):
        if item.get("uid") == uid:
            flags = item.get("flags", [])
            break
    to_list = [addr for _, addr in getaddresses([str(msg.get("To") or "")]) if addr]
    cc_list = [addr for _, addr in getaddresses([str(msg.get("Cc") or "")]) if addr]
    bcc_list = [addr for _, addr in getaddresses([str(msg.get("Bcc") or "")]) if addr]
    body_text, body_html = _extract_body(msg)

    return EmailFullItem(
        uid=uid,
        from_=str(msg.get("From") or ""),
        to=to_list,
        subject=str(msg.get("Subject") or "(no subject)"),
        date=str(msg.get("Date") or ""),
        is_read="S" in flags,
        is_flagged="F" in flags,
        has_attachments=_message_has_attachments(msg),
        folder=folder,
        preview=_message_preview(msg),
        body_text=body_text,
        body_html=body_html,
        cc=cc_list,
        bcc=bcc_list,
        reply_to=str(msg.get("Reply-To") or "") or None,
        message_id=str(msg.get("Message-ID") or uid),
        attachments=[],
        read_receipt_token=None,
        is_pgp_encrypted=False,
    )


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
    return {"message_id": result.get("message_id", "")}
