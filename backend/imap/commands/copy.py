from __future__ import annotations

from backend.imap import maildir
from backend.imap.session import ImapSession


async def run(session: ImapSession, uid: str, destination: str) -> str:
    if not session.is_authenticated or not session.maildir_path or not session.selected_mailbox:
        return "NO mailbox not selected"

    raw = maildir.read_message(session.maildir_path, session.selected_mailbox, uid)
    if raw is None:
        return "NO no such message"
    new_uid = maildir.write_message(session.maildir_path, destination, raw)
    return f"OK [COPYUID 1 {uid} {new_uid}] COPY completed"
