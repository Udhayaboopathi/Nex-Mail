from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class GenericListResponse(BaseModel):
    items: list[str]


class GenericActionResponse(BaseModel):
    success: bool
    message: str
