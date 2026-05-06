from fastapi import APIRouter
from backend.schemas.common import GenericListResponse

router = APIRouter(tags=['templates'])

@router.get('/', response_model=GenericListResponse)
async def list_items() -> GenericListResponse:
    return GenericListResponse(items=[])
