from __future__ import annotations

from backend.imap import maildir
from backend.imap.session import ImapSession


async def run(session: ImapSession, mailbox_name: str, literal: str = "") -> str:
    if not session.is_authenticated or not session.maildir_path:
        return "NO authenticate first"
    uid = maildir.write_message(session.maildir_path, mailbox_name, literal.encode(), "")
    return f"OK [APPENDUID 1 {uid}] APPEND completed"
