from collections.abc import AsyncGenerator
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import AsyncSessionLocal
from backend.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/auth/login')

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, str]:
    try:
        payload = decode_token(token)
        return {'id': payload.get('sub', '')}
    except JWTError as exc:
        raise HTTPException(status_code=401, detail='Invalid token') from exc
