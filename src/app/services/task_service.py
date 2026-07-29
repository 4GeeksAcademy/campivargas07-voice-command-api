"""
In-memory task storage.
All data lives in a module-level list and resets on server restart.
No database or filesystem used.
"""

from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate

# Module-level in-memory storage
_tasks: list[Task] = []
_next_id: int = 1


def _assign_id() -> int:
    global _next_id  # noqa: PLW0603
    tid = _next_id
    _next_id += 1
    return tid


def get_all() -> list[Task]:
    """Return all tasks."""
    return list(_tasks)


def get_by_id(task_id: int) -> Task | None:
    """Return a task by id, or None if not found."""
    for task in _tasks:
        if task.id == task_id:
            return task
    return None


def create(payload: TaskCreate) -> Task:
    """Create a new task and return it."""
    task = Task(id=_assign_id(), title=payload.title, done=payload.done)
    _tasks.append(task)
    return task


def replace(task_id: int, payload: TaskReplace) -> Task | None:
    """Fully replace a task. Returns None if not found."""
    for i, task in enumerate(_tasks):
        if task.id == task_id:
            updated = Task(id=task_id, title=payload.title, done=payload.done)
            _tasks[i] = updated
            return updated
    return None


def update(task_id: int, payload: TaskUpdate) -> Task | None:
    """Partially update a task. Returns None if not found."""
    for i, task in enumerate(_tasks):
        if task.id == task_id:
            new_title = payload.title if payload.title is not None else task.title
            new_done = payload.done if payload.done is not None else task.done
            updated = Task(id=task_id, title=new_title, done=new_done)
            _tasks[i] = updated
            return updated
    return None


def delete(task_id: int) -> bool:
    """Delete a task by id. Returns True if deleted, False if not found."""
    for i, task in enumerate(_tasks):
        if task.id == task_id:
            _tasks.pop(i)
            return True
    return False
