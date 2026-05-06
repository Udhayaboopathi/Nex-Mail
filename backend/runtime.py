"""Process-wide asyncio loop used by the FastAPI app (for thread-safe scheduling from aiosmtpd)."""

from __future__ import annotations

import asyncio

_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def get_main_loop() -> asyncio.AbstractEventLoop:
    if _main_loop is None:
        raise RuntimeError("main event loop not initialized (lifespan not started)")
    return _main_loop
