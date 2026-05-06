from __future__ import annotations

from backend.imap import maildir
from backend.imap.session import ImapSession


async def run(session: ImapSession, mailbox_name: str = "INBOX") -> str:
    if not session.is_authenticated or not session.maildir_path:
        return "NO authenticate first"

    selected = mailbox_name.strip('"') or "INBOX"
    stats = maildir.folder_stats(session.maildir_path, selected)
    session.select_mailbox(selected)
    return (
        f"* {stats['exists']} EXISTS\r\n"
        f"* {stats['recent']} RECENT\r\n"
        f"* OK [UNSEEN {stats['unseen']}]\r\n"
        f"* OK [UIDVALIDITY {stats['uidvalidity']}]\r\n"
        f"* OK [UIDNEXT {stats['uidnext']}]\r\n"
        "* FLAGS (\\Seen \\Answered \\Flagged \\Deleted \\Draft)\r\n"
        f"OK [READ-WRITE] SELECT {selected} completed"
    )
