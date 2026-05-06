from __future__ import annotations

from backend.imap import maildir
from backend.imap.commands.copy import run as copy_run
from backend.imap.session import ImapSession


async def run(session: ImapSession, uid: str, destination: str) -> str:
    copied = await copy_run(session, uid, destination)
    if copied.startswith("NO"):
        return copied
    maildir.delete_message(session.maildir_path or "", session.selected_mailbox or "INBOX", uid)
    return copied.replace("COPY completed", "MOVE completed")
