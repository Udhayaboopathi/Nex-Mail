from __future__ import annotations

import asyncio

from backend.imap import maildir
from backend.imap.session import ImapSession


async def run(session: ImapSession, timeout_seconds: int = 30) -> str:
    if not session.is_authenticated or not session.maildir_path or not session.selected_mailbox:
        return "NO mailbox not selected"

    before = maildir.folder_stats(session.maildir_path, session.selected_mailbox)["exists"]
    await asyncio.sleep(timeout_seconds)
    after = maildir.folder_stats(session.maildir_path, session.selected_mailbox)["exists"]
    if after > before:
        return f"* {after} EXISTS"
    return "OK IDLE terminated"
