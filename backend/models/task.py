"""
Task document model (Beanie ODM → MongoDB).

Mirrors the Mongoose Task schema:
  - title       (str, max 100, required)
  - description (str, max 500, optional)
  - status      (enum: todo | in-progress | done)
  - priority    (enum: low | medium | high)
  - user        (PydanticObjectId — owner reference)
  - created_at / updated_at
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in-progress"
    done = "done"


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Task(Document):
    title: str = Field(..., max_length=100)
    description: str = Field(default="", max_length=500)
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.medium
    user: PydanticObjectId          # owner's User._id
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "tasks"

    model_config = {"populate_by_name": True}
