"""
Request and response schemas for the /api/tasks routes.
"""

from typing import Optional
from pydantic import BaseModel, Field
from models.task import TaskStatus, TaskPriority


# ── Request bodies ────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.medium


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None


# ── Response shapes ───────────────────────────────────────────────────────────

class TaskOut(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    user: str
    created_at: str
    updated_at: str

    @classmethod
    def from_doc(cls, task) -> "TaskOut":
        """Convert a Beanie Task document to the wire format."""
        return cls(
            id=str(task.id),
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            user=str(task.user),
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
        )
