"""
task_service.py
~~~~~~~~~~~~~~~
CRUD business logic for tasks.
Direct port of Node.js taskService.js.

All operations are scoped to the authenticated user (ownership enforced).
"""

from datetime import datetime
from typing import Optional

from beanie import PydanticObjectId
from fastapi import HTTPException, status

from models.task import Task, TaskPriority, TaskStatus


async def get_tasks(
    user_id: PydanticObjectId,
    status_filter: Optional[TaskStatus] = None,
    priority_filter: Optional[TaskPriority] = None,
) -> list[Task]:
    """Return all tasks owned by *user_id*, newest first."""
    query = Task.find(Task.user == user_id)
    if status_filter:
        query = query.find(Task.status == status_filter)
    if priority_filter:
        query = query.find(Task.priority == priority_filter)
    return await query.sort(-Task.created_at).to_list()


async def get_task_by_id(task_id: str, user_id: PydanticObjectId) -> Task:
    """
    Return a single task by ID, verifying ownership.

    Raises:
        HTTPException 400 — invalid ObjectId format
        HTTPException 404 — task not found or not owned by user
    """
    try:
        oid = PydanticObjectId(task_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task ID")

    task = await Task.find_one(Task.id == oid, Task.user == user_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def create_task(user_id: PydanticObjectId, data: dict) -> Task:
    """Create and persist a new task owned by *user_id*."""
    task = Task(user=user_id, **data)
    await task.insert()
    return task


async def update_task(task_id: str, user_id: PydanticObjectId, updates: dict) -> Task:
    """
    Apply *updates* to an existing task, verifying ownership.

    Raises:
        HTTPException 400 — invalid ObjectId
        HTTPException 404 — task not found or not owned by user
    """
    task = await get_task_by_id(task_id, user_id)

    # Apply only the fields that were actually provided (partial update).
    for field, value in updates.items():
        if value is not None:
            setattr(task, field, value)
    task.updated_at = datetime.utcnow()
    await task.save()
    return task


async def delete_task(task_id: str, user_id: PydanticObjectId) -> None:
    """
    Delete a task, verifying ownership.

    Raises:
        HTTPException 400 — invalid ObjectId
        HTTPException 404 — task not found or not owned by user
    """
    task = await get_task_by_id(task_id, user_id)
    await task.delete()
