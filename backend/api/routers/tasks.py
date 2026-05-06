from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import Task

router = APIRouter(tags=["tasks"])


class TaskItem(BaseModel):
    id: str
    title: str
    description: str | None = None
    due_at: str | None = None
    is_completed: bool
    completed_at: str | None = None
    priority: str
    linked_email_uid: str | None = None
    created_at: str


class CreateTaskRequest(BaseModel):
    mailbox_id: str
    title: str = Field(min_length=1)
    description: str | None = None
    due_at: str | None = None
    priority: str = "normal"
    linked_email_uid: str | None = None


class UpdateTaskRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    due_at: str | None = None
    priority: str | None = None
    linked_email_uid: str | None = None


def _to_item(t: Task) -> TaskItem:
    return TaskItem(
        id=str(t.id),
        title=t.title or "",
        description=t.description,
        due_at=t.due_at.isoformat() if t.due_at else None,
        is_completed=bool(t.is_completed),
        completed_at=t.completed_at.isoformat() if t.completed_at else None,
        priority=t.priority or "normal",
        linked_email_uid=t.linked_email_uid,
        created_at=t.created_at.isoformat() if t.created_at else "",
    )


@router.get("/", response_model=list[TaskItem])
async def list_tasks(user: dict = Depends(require_any_auth)) -> list[TaskItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Task).order_by(Task.created_at.desc()))).scalars().all()
    return [_to_item(t) for t in rows]


@router.post("/", response_model=TaskItem)
async def create_task(payload: CreateTaskRequest, user: dict = Depends(require_any_auth)) -> TaskItem:
    try:
        mailbox_uuid = UUID(payload.mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    due_at = datetime.fromisoformat(payload.due_at) if payload.due_at else None
    async with AsyncSessionLocal() as db:
        task = Task(
            mailbox_id=mailbox_uuid,
            title=payload.title,
            description=payload.description,
            due_at=due_at,
            priority=payload.priority,
            linked_email_uid=payload.linked_email_uid,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
    return _to_item(task)


@router.patch("/{task_id}", response_model=TaskItem)
async def update_task(task_id: str, payload: UpdateTaskRequest, user: dict = Depends(require_any_auth)) -> TaskItem:
    try:
        task_uuid = UUID(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid task_id") from exc
    async with AsyncSessionLocal() as db:
        task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalar_one_or_none()
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        if payload.title is not None:
            task.title = payload.title
        if payload.description is not None:
            task.description = payload.description
        if payload.due_at is not None:
            task.due_at = datetime.fromisoformat(payload.due_at)
        if payload.priority is not None:
            task.priority = payload.priority
        if payload.linked_email_uid is not None:
            task.linked_email_uid = payload.linked_email_uid
        task.updated_at = datetime.now(tz=timezone.utc)
        await db.commit()
        await db.refresh(task)
    return _to_item(task)


@router.post("/{task_id}/complete", response_model=TaskItem)
async def complete_task(task_id: str, user: dict = Depends(require_any_auth)) -> TaskItem:
    try:
        task_uuid = UUID(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid task_id") from exc
    async with AsyncSessionLocal() as db:
        task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalar_one_or_none()
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        task.is_completed = True
        task.completed_at = datetime.now(tz=timezone.utc)
        task.updated_at = datetime.now(tz=timezone.utc)
        await db.commit()
        await db.refresh(task)
    return _to_item(task)


@router.delete("/{task_id}")
async def delete_task(task_id: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        task_uuid = UUID(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid task_id") from exc
    async with AsyncSessionLocal() as db:
        task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalar_one_or_none()
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        await db.delete(task)
        await db.commit()
    return {"ok": True}
