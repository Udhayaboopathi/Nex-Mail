from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from backend.database import AsyncSessionLocal
from backend.models import Domain, Mailbox, User

router = APIRouter(tags=["super_admin"])


class SuperAdminStats(BaseModel):
    domains: int
    mailboxes: int
    users: int


@router.get("/stats", response_model=SuperAdminStats)
async def get_stats() -> SuperAdminStats:
    async with AsyncSessionLocal() as db:
        domains = int(await db.scalar(select(func.count(Domain.id))) or 0)
        mailboxes = int(await db.scalar(select(func.count(Mailbox.id))) or 0)
        users = int(await db.scalar(select(func.count(User.id))) or 0)
    return SuperAdminStats(domains=domains, mailboxes=mailboxes, users=users)
