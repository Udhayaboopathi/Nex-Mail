import asyncio
from sqlalchemy import select
from backend.database import AsyncSessionLocal
from backend.models.user import User
from backend.core.security import hash_password
from backend.config import settings

async def seed() -> None:
    async with AsyncSessionLocal() as db:
        found = await db.execute(select(User).where(User.email == settings.super_admin_email))
        if found.scalar_one_or_none() is None:
            db.add(User(email=settings.super_admin_email, hashed_password=hash_password(settings.super_admin_password), role='super_admin'))
            await db.commit()

if __name__ == '__main__':
    asyncio.run(seed())
