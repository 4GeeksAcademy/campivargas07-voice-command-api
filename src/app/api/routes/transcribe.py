from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.datastructures import UploadFile

from src.app.api.routes.instruction import route_instruction_text
from src.app.schemas.voice import InstructionPayload, TranscribeFlowResponse
from src.app.services import log_service, task_service
from src.app.services.groq_service import transcribe_audio

router = APIRouter(tags=["transcribe"])


@router.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/transcribe", response_model=TranscribeFlowResponse)
async def transcribe_and_run_flow(request: Request) -> TranscribeFlowResponse:
    content_type = request.headers.get("content-type", "").lower()

    # --- Case 1: multipart/form-data (audio from microphone) ---
    if "multipart/form-data" in content_type:
        form = await request.form()
        file_field: UploadFile | None = form.get("file")  # type: ignore[assignment]
        if file_field is None or not file_field.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'file' field in multipart upload.",
            )

        raw_bytes = await file_field.read()
        if not raw_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio file is empty.",
            )

        language: str | None = form.get("language")  # type: ignore[assignment]
        if language and not language.strip():
            language = None

        transcription = transcribe_audio(
            raw_bytes,
            filename=file_field.filename or "audio.webm",
            language=language,
        )

    # --- Case 2: application/json (manual text transcription) ---
    elif "application/json" in content_type:
        body = await request.json()
        transcription = (body or {}).get("transcription", "")
        if not transcription or not transcription.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing or empty 'transcription' in JSON body.",
            )
        transcription = transcription.strip()

    # --- Case 3: unsupported content type ---
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type: {content_type}. Use multipart/form-data or application/json.",
        )

    # --- Route the intent via Groq LLM ---
    instruction: InstructionPayload = route_instruction_text(transcription)

    # --- Execute the action against the in-memory task service ---
    result = _execute_instruction(instruction)

    # --- Log the transcription to JSON Lines file ---
    log_service.append_log(
        transcription=transcription,
        instruction=instruction.model_dump() if hasattr(instruction, "model_dump") else instruction.__dict__,
        result=result,
    )

    return TranscribeFlowResponse(
        transcription=transcription,
        instruction=instruction,
        result=result,
    )


def _execute_instruction(instruction: InstructionPayload) -> Any:
    """Execute a routed instruction against the task service."""
    method = instruction.method.upper()
    endpoint = instruction.endpoint.rstrip("/")
    params = instruction.params or {}

    # Normalise endpoint: strip /tasks prefix
    if endpoint == "/tasks" or endpoint == "":
        endpoint = "tasks"

    if endpoint != "tasks":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unknown endpoint: {endpoint}",
        )

    # --- Parse task_id from params ---
    task_id: int | None = params.get("task_id")
    if task_id is None:
        # Some LLMs may put the id in a different field or in the endpoint path
        pass

    if method == "GET":
        return task_service.get_all()

    elif method == "POST":
        title = params.get("title", "")
        if not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'title' in params for POST /tasks.",
            )
        from src.app.schemas.voice import TaskCreate
        return task_service.create(TaskCreate(title=title, done=params.get("done", False)))

    elif method == "PUT":
        if task_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'task_id' in params for PUT /tasks/{id}.",
            )
        title = params.get("title", "")
        if not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'title' in params for PUT /tasks/{id}.",
            )
        from src.app.schemas.voice import TaskReplace
        task = task_service.replace(task_id, TaskReplace(title=title, done=params.get("done", False)))
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found.",
            )
        return task

    elif method == "PATCH":
        if task_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'task_id' in params for PATCH /tasks/{id}.",
            )
        from src.app.schemas.voice import TaskUpdate
        task = task_service.update(
            task_id,
            TaskUpdate(
                title=params.get("title"),
                done=params.get("done"),
            ),
        )
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found.",
            )
        return task

    elif method == "DELETE":
        if task_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'task_id' in params for DELETE /tasks/{id}.",
            )
        deleted = task_service.delete(task_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found.",
            )
        return {"message": f"Task {task_id} deleted."}

    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unsupported method: {method}",
        )
