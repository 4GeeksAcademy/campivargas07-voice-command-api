from fastapi import APIRouter, HTTPException, status

from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate
from src.app.services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
def get_tasks() -> list[Task]:
    return task_service.get_all()


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate) -> Task:
    return task_service.create(payload)


@router.get("/{task_id}", response_model=Task)
def get_task(task_id: int) -> Task:
    task = task_service.get_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found.",
        )
    return task


@router.put("/{task_id}", response_model=Task)
def replace_task(
    task_id: int,
    payload: TaskReplace,
) -> Task:
    task = task_service.replace(task_id, payload)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found.",
        )
    return task


@router.patch("/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    payload: TaskUpdate,
) -> Task:
    task = task_service.update(task_id, payload)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found.",
        )
    return task


@router.delete("/{task_id}")
def delete_task(task_id: int) -> dict[str, str]:
    deleted = task_service.delete(task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found.",
        )
    return {"message": f"Task {task_id} deleted."}
