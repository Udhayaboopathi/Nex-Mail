from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ImapSession:
    state: str = "NOT_AUTHENTICATED"
    username: str | None = None
    selected_mailbox: str | None = None
    maildir_path: str | None = None
    idle_mode: bool = False
    pending: list[str] = field(default_factory=list)
    capabilities: list[str] = field(
        default_factory=lambda: ["IMAP4rev1", "UIDPLUS", "IDLE", "MOVE", "AUTH=PLAIN", "AUTH=LOGIN"]
    )

    @property
    def is_authenticated(self) -> bool:
        return self.state in {"AUTHENTICATED", "SELECTED"}

    def mark_authenticated(self, username: str, maildir_path: str) -> None:
        self.username = username
        self.maildir_path = maildir_path
        self.state = "AUTHENTICATED"

    def select_mailbox(self, mailbox: str) -> None:
        self.selected_mailbox = mailbox
        self.state = "SELECTED"

    def logout(self) -> None:
        self.state = "LOGOUT"
