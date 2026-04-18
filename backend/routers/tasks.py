"""
routers/tasks.py
~~~~~~~~~~~~~~~~
Task CRUD routes — exact API-compatible replacement for the Node.js Express routes:

  GET    /api/tasks          →  list tasks (optional ?status= ?priority= filters)
  POST   /api/tasks          →  create a task
  GET    /api/tasks/{id}     →  get a single task
  PUT    /api/tasks/{id}     →  update a task
  DELETE /api/tasks/{id}     →  delete a task

All routes require a valid JWT (enforced by get_current_user dependency).
Response envelope matches the Node.js format:
  { success: true, count?: N, data: {...} }
"""

from typing import Optional

from fastapi import APIRouter, Depends, status

from core.dependencies import get_current_user
from models.task import TaskPriority, TaskStatus
from models.user import User
from schemas.task import TaskCreate, TaskOut, TaskUpdate
from services import task_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", status_code=status.HTTP_200_OK)
async def list_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    current_user: User = Depends(get_current_user),
):
    tasks = await task_service.get_tasks(
        user_id=current_user.id,
        status_filter=status,
        priority_filter=priority,
    )
    return {
        "success": True,
        "count": len(tasks),
        "data": [TaskOut.from_doc(t) for t in tasks],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    current_user: User = Depends(get_current_user),
):
    task = await task_service.create_task(
        user_id=current_user.id,
        data=body.model_dump(),
    )
    return {
        "success": True,
        "message": "Task created successfully",
        "data": TaskOut.from_doc(task),
    }


@router.get("/{task_id}", status_code=status.HTTP_200_OK)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    task = await task_service.get_task_by_id(task_id, current_user.id)
    return {"success": True, "data": TaskOut.from_doc(task)}


@router.put("/{task_id}", status_code=status.HTTP_200_OK)
async def update_task(
    task_id: str,
    body: TaskUpdate,
    current_user: User = Depends(get_current_user),
):
    updates = body.model_dump(exclude_none=True)
    task = await task_service.update_task(task_id, current_user.id, updates)
    return {
        "success": True,
        "message": "Task updated successfully",
        "data": TaskOut.from_doc(task),
    }


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    await task_service.delete_task(task_id, current_user.id)
    return {"success": True, "message": "Task deleted successfully"}
