from fastapi import APIRouter
from backend.schemas.common import GenericListResponse

router = APIRouter(tags=['api_keys'])

@router.get('/', response_model=GenericListResponse)
async def list_items() -> GenericListResponse:
    return GenericListResponse(items=[])
