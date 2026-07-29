from fastapi import APIRouter

from src.app.schemas.voice import InstructionPayload, InstructionRequest
from src.app.services.groq_service import route_intent

router = APIRouter(tags=["instruction"])

# Reusable function so /transcribe can route without a second HTTP call
def route_instruction_text(transcription: str) -> InstructionPayload:
    """Parse a transcription and return a structured instruction payload."""
    raw = route_intent(transcription)
    return InstructionPayload(
        endpoint=raw.get("endpoint", "/tasks"),
        method=raw.get("method", "GET"),
        params=raw.get("params", {}),
    )


@router.post("/instruction", response_model=InstructionPayload)
def route_instruction(
    payload: InstructionRequest,
) -> InstructionPayload:
    return route_instruction_text(payload.transcription)
