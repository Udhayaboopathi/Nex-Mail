from fastapi import APIRouter, HTTPException

from backend.schemas.auth import LoginRequest, LoginResponse, TokenPair
from backend.services.auth_service import create_access_token, create_refresh_token

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    if payload.password != "change-immediately":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access = await create_access_token(payload.email)
    refresh = await create_refresh_token(payload.email)
    return LoginResponse(role="super_admin", tokens=TokenPair(access_token=access, refresh_token=refresh))
