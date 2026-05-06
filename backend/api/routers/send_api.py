from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from backend.tasks.delivery import deliver_email

router = APIRouter(tags=["send_api"])


class SendPayload(BaseModel):
    from_addr: EmailStr
    to_list: list[EmailStr]
    subject: str
    body_text: str
    body_html: str | None = None


class SendResponse(BaseModel):
    queued: bool
    task_id: str


@router.post("/send", response_model=SendResponse)
async def queue_send(payload: SendPayload) -> SendResponse:
    async_result = deliver_email.delay(payload.model_dump(mode="json"))
    return SendResponse(queued=True, task_id=async_result.id)
