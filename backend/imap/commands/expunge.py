from __future__ import annotations

from backend.imap import maildir
from backend.imap.session import ImapSession


async def run(session: ImapSession) -> str:
    if not session.is_authenticated or not session.maildir_path or not session.selected_mailbox:
        return "NO mailbox not selected"

    lines: list[str] = []
    for i, msg in enumerate(maildir.list_messages(session.maildir_path, session.selected_mailbox), 1):
        if "T" in msg["flags"]:
            if maildir.delete_message(session.maildir_path, session.selected_mailbox, msg["uid"]):
                lines.append(f"* {i} EXPUNGE")
    return "\r\n".join(lines) if lines else "OK EXPUNGE completed"
