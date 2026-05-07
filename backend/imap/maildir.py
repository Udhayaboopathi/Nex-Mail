from __future__ import annotations

from email.parser import BytesParser
from email.policy import default
from mailbox import Maildir
from pathlib import Path
from typing import Any


def _folder_path(maildir_path: str, folder: str) -> Path:
    normalized = folder.strip('"') or "INBOX"
    base = Path(maildir_path)
    return base if normalized.upper() == "INBOX" else base / f".{normalized}"


def _maildir(maildir_path: str, folder: str) -> Maildir:
    # Ensure mailbox root exists with required Maildir subfolders.
    base = Path(maildir_path)
    base.mkdir(parents=True, exist_ok=True)
    for sub in ("cur", "new", "tmp"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    return Maildir(_folder_path(maildir_path, folder).as_posix(), create=True)


def list_folders(maildir_path: str) -> list[str]:
    root = Path(maildir_path)
    folders = ["INBOX"]
    for sub in root.glob(".*"):
        if sub.is_dir() and (sub / "cur").exists():
            folders.append(sub.name[1:])
    return sorted(set(folders))


def list_messages(maildir_path: str, folder: str) -> list[dict[str, Any]]:
    md = _maildir(maildir_path, folder)
    messages: list[dict[str, Any]] = []
    for key in md.iterkeys():
        msg = md.get_message(key)
        flags = sorted(msg.get_flags()) if hasattr(msg, "get_flags") else []
        messages.append(
            {
                "uid": str(key),
                "flags": flags,
                "size": len(msg.as_bytes()),
                "internaldate": msg.get("Date") or "",
            }
        )
    return messages


def read_message(maildir_path: str, folder: str, uid: str) -> bytes | None:
    md = _maildir(maildir_path, folder)
    if uid not in md:
        return None
    return md.get_message(uid).as_bytes()


def write_message(maildir_path: str, folder: str, raw_bytes: bytes, flags: str = "") -> str:
    md = _maildir(maildir_path, folder)
    message = BytesParser(policy=default).parsebytes(raw_bytes)
    if hasattr(message, "set_flags"):
        message.set_flags(flags)
    return str(md.add(message))


def set_flags(maildir_path: str, folder: str, uid: str, flags: str) -> bool:
    md = _maildir(maildir_path, folder)
    if uid not in md:
        return False
    msg = md.get_message(uid)
    if hasattr(msg, "set_flags"):
        msg.set_flags(flags)
    md[uid] = msg
    return True


def delete_message(maildir_path: str, folder: str, uid: str) -> bool:
    md = _maildir(maildir_path, folder)
    if uid not in md:
        return False
    md.remove(uid)
    return True


def folder_stats(maildir_path: str, folder: str) -> dict[str, int]:
    entries = list_messages(maildir_path, folder)
    unseen = sum(1 for item in entries if "S" not in item["flags"])
    return {
        "exists": len(entries),
        "recent": len(entries),
        "unseen": unseen,
        "uidvalidity": 1,
        "uidnext": len(entries) + 1,
    }
