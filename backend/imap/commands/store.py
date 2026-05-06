from __future__ import annotations

from backend.imap import maildir
from backend.imap.session import ImapSession

FLAG_MAP = {"\\Seen": "S", "\\Answered": "R", "\\Flagged": "F", "\\Deleted": "T", "\\Draft": "D"}


def _imap_to_maildir(flags: str) -> str:
    chars = [FLAG_MAP[token] for token in flags.split() if token in FLAG_MAP]
    return "".join(sorted(set(chars)))


async def run(session: ImapSession, uid: str, mode: str, flags: str) -> str:
    if not session.is_authenticated or not session.maildir_path or not session.selected_mailbox:
        return "NO mailbox not selected"

    md_flags = _imap_to_maildir(flags.strip("()"))
    if mode.startswith("+"):
        current = next((m for m in maildir.list_messages(session.maildir_path, session.selected_mailbox) if m["uid"] == uid), None)
        base = "".join(current["flags"]) if current else ""
        md_flags = "".join(sorted(set(base + md_flags)))
    elif mode.startswith("-"):
        current = next((m for m in maildir.list_messages(session.maildir_path, session.selected_mailbox) if m["uid"] == uid), None)
        base = set("".join(current["flags"])) if current else set()
        md_flags = "".join(sorted(base - set(md_flags)))

    if not maildir.set_flags(session.maildir_path, session.selected_mailbox, uid, md_flags):
        return "NO no such message"
    return f"* {uid} FETCH (FLAGS ({flags.strip()}))"
