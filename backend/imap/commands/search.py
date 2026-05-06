from __future__ import annotations

from email.parser import BytesParser
from email.policy import default

from backend.imap import maildir
from backend.imap.session import ImapSession


async def run(session: ImapSession, *criteria: str) -> str:
    if not session.is_authenticated or not session.maildir_path or not session.selected_mailbox:
        return "NO mailbox not selected"

    terms = [c.upper() for c in criteria] or ["ALL"]
    messages = maildir.list_messages(session.maildir_path, session.selected_mailbox)
    matched: list[str] = []

    for item in messages:
        raw = maildir.read_message(session.maildir_path, session.selected_mailbox, item["uid"])
        if raw is None:
            continue
        parsed = BytesParser(policy=default).parsebytes(raw)
        haystack = " ".join([
            parsed.get("From", ""), parsed.get("To", ""), parsed.get("Cc", ""), parsed.get("Subject", ""), str(parsed.get_payload()),
        ]).upper()
        if "ALL" in terms:
            matched.append(item["uid"])
            continue
        if any(token in haystack for token in terms if token not in {"UNSEEN", "SEEN"}):
            matched.append(item["uid"])
            continue
        if "UNSEEN" in terms and "S" not in item["flags"]:
            matched.append(item["uid"])
            continue
        if "SEEN" in terms and "S" in item["flags"]:
            matched.append(item["uid"])

    return "* SEARCH " + " ".join(matched)
