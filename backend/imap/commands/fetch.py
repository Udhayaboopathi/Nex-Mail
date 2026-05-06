from __future__ import annotations

from email.parser import BytesParser
from email.policy import default

from backend.imap import maildir
from backend.imap.session import ImapSession


async def run(session: ImapSession, uid: str = "1", section: str = "RFC822") -> str:
    if not session.is_authenticated or not session.maildir_path or not session.selected_mailbox:
        return "NO mailbox not selected"

    raw = maildir.read_message(session.maildir_path, session.selected_mailbox, uid)
    if raw is None:
        return "NO no such message"

    parsed = BytesParser(policy=default).parsebytes(raw)
    flags = "(" + " ".join([f"\\{flag}" for flag in sorted(parsed.get_flags())]) + ")" if hasattr(parsed, "get_flags") else "()"
    requested = section.upper()
    if requested in {"RFC822", "BODY[]"}:
        payload = raw.decode(errors="ignore")
    elif requested in {"RFC822.HEADER", "BODY[HEADER]"}:
        payload = str(parsed)
    elif requested in {"BODY[TEXT]"}:
        payload = parsed.get_body(preferencelist=("plain", "html")).get_content() if parsed.is_multipart() else parsed.get_payload()
    elif requested == "RFC822.SIZE":
        return f"* {uid} FETCH (RFC822.SIZE {len(raw)})"
    else:
        payload = raw.decode(errors="ignore")

    return f"* {uid} FETCH (UID {uid} FLAGS {flags} {requested} {{{len(payload)}}}\\r\\n{payload})"
