from __future__ import annotations

import asyncio
import ssl
from typing import Awaitable, Callable

from backend.imap.session import ImapSession
from backend.imap.commands import login, select, fetch, search, store, expunge, copy, move, append, idle


IMAP_COMMANDS: dict[str, Callable[..., Awaitable[str]]] = {
    "LOGIN": login.run,
    "SELECT": select.run,
    "FETCH": fetch.run,
    "SEARCH": search.run,
    "STORE": store.run,
    "EXPUNGE": expunge.run,
    "COPY": copy.run,
    "MOVE": move.run,
    "APPEND": append.run,
    "IDLE": idle.run,
}


async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    session = ImapSession()
    writer.write(b"* OK [CAPABILITY IMAP4rev1 UIDPLUS IDLE MOVE AUTH=PLAIN AUTH=LOGIN] Nex Mail IMAP ready\r\n")
    await writer.drain()
    try:
        while not reader.at_eof() and session.state != "LOGOUT":
            raw = await reader.readline()
            if not raw:
                break
            line = raw.decode(errors="ignore").strip()
            if not line:
                continue
            parts = line.split(" ")
            tag = parts[0]
            cmd = parts[1].upper() if len(parts) > 1 else "NOOP"
            args = parts[2:]
            if cmd == "LOGOUT":
                session.logout()
                writer.write(b"* BYE logging out\r\n")
                writer.write(f"{tag} OK LOGOUT completed\r\n".encode())
                await writer.drain()
                break
            if cmd == "CAPABILITY":
                writer.write(b"* CAPABILITY IMAP4rev1 UIDPLUS IDLE MOVE AUTH=PLAIN AUTH=LOGIN\r\n")
                writer.write(f"{tag} OK CAPABILITY completed\r\n".encode())
                await writer.drain()
                continue
            handler = IMAP_COMMANDS.get(cmd)
            if handler is None:
                writer.write(f"{tag} BAD Unsupported command\r\n".encode())
                await writer.drain()
                continue
            response = await handler(session, *args)
            for ln in response.splitlines():
                writer.write(f"{ln}\r\n".encode())
            writer.write(f"{tag} OK {cmd} completed\r\n".encode())
            await writer.drain()
    finally:
        if not writer.is_closing():
            writer.write(b"* BYE connection closed\r\n")
            await writer.drain()
        writer.close()
        await writer.wait_closed()


async def create_imap_server() -> asyncio.base_events.Server:
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain("/etc/ssl/mail/fullchain.pem", "/etc/ssl/mail/privkey.pem")
    return await asyncio.start_server(_handle_client, host="0.0.0.0", port=993, ssl=ctx)
