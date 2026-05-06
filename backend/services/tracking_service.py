from __future__ import annotations

async def health() -> dict[str, str]:
    return {'service': 'ok'}
