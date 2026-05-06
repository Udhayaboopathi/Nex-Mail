import httpx

async def lookup_ip(ip: str | None) -> str:
    if not ip:
        return "unknown"
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"http://ip-api.com/json/{ip}")
            data = r.json()
            return f"{data.get('city', '')}, {data.get('country', '')}".strip(", ") or "unknown"
    except Exception:
        return "unknown"
