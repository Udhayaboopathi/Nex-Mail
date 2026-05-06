from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from backend.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(value: str) -> str:
    return pwd_context.hash(value)

def verify_password(value: str, hashed: str) -> bool:
    return pwd_context.verify(value, hashed)

def create_token(sub: str, expires_delta: timedelta, extra: dict | None = None) -> str:
    exp = datetime.now(tz=timezone.utc) + expires_delta
    payload: dict = {"sub": sub, "exp": exp}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
