"""Route to view transcription logs."""

from fastapi import APIRouter, Query

from src.app.services import log_service

router = APIRouter(tags=["logs"])


@router.get("/logs")
async def get_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """Return recent transcription log entries (newest first)."""
    entries = log_service.read_logs(limit=limit, offset=offset)
    total = log_service.count_logs()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "entries": entries,
    }


@router.get("/logs/file-path")
async def get_log_file_path() -> dict:
    """Return the filesystem path to the log file (for professors to inspect)."""
    return {
        "file_path": log_service.get_log_file_path(),
        "format": "jsonl",
        "description": "One JSON object per line. Each entry has: timestamp, transcription, instruction, result, status.",
    }