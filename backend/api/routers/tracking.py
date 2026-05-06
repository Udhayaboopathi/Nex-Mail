import base64
from datetime import datetime, timezone

from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import TrackingPixel, LinkClick

router = APIRouter(tags=["tracking"])

# Minimal 1x1 transparent GIF
_PIXEL_GIF = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


@router.get("/px/{token}.gif")
async def tracking_pixel(token: str) -> Response:
    async with AsyncSessionLocal() as db:
        pixel = (await db.execute(
            select(TrackingPixel).where(TrackingPixel.token == token)
        )).scalar_one_or_none()
        if pixel:
            from backend.models import ReadReceipt
            receipt = (await db.execute(
                select(ReadReceipt).where(ReadReceipt.id == pixel.read_receipt_id)
            )).scalar_one_or_none()
            if receipt:
                if receipt.opened_at is None:
                    receipt.opened_at = datetime.now(tz=timezone.utc)
                receipt.open_count = int(receipt.open_count or 0) + 1
                await db.commit()
    return Response(content=_PIXEL_GIF, media_type="image/gif", headers={"Cache-Control": "no-store, no-cache"})


@router.get("/click/{token}")
async def track_click(token: str) -> RedirectResponse:
    target = "https://example.com"
    async with AsyncSessionLocal() as db:
        click = (await db.execute(
            select(LinkClick).where(LinkClick.tracking_token == token)
        )).scalar_one_or_none()
        if click:
            target = click.original_url or target
            now = datetime.now(tz=timezone.utc)
            click.click_count = int(click.click_count or 0) + 1
            if click.first_clicked_at is None:
                click.first_clicked_at = now
            click.last_clicked_at = now
            await db.commit()
    return RedirectResponse(url=target, status_code=302)
