"""
JSON Lines log service.
Appends one JSON object per line to logs/transcriptions.jsonl.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "transcriptions.jsonl")


def _ensure_log_dir() -> None:
    """Create the logs directory if it doesn't exist."""
    os.makedirs(_LOG_DIR, exist_ok=True)


def append_log(
    transcription: str,
    instruction: dict[str, Any],
    result: Any,
    status: str = "ok",
) -> dict[str, Any]:
    """Append one log entry to the JSON Lines file.

    Returns the entry that was written, in case the caller wants to use it.
    """
    _ensure_log_dir()

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "transcription": transcription,
        "instruction": instruction,
        "result": result,
        "status": status,
    }

    with open(_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    return entry


def read_logs(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """Read log entries from the JSON Lines file, newest first.

    Args:
        limit: Maximum number of entries to return.
        offset: Number of entries to skip (for pagination).

    Returns:
        A list of log entry dicts.
    """
    _ensure_log_dir()

    if not os.path.exists(_LOG_FILE):
        return []

    entries: list[dict[str, Any]] = []
    with open(_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # skip malformed lines

    # Newest first
    entries.reverse()
    return entries[offset:offset + limit]


def count_logs() -> int:
    """Return the total number of log entries."""
    _ensure_log_dir()

    if not os.path.exists(_LOG_FILE):
        return 0

    count = 0
    with open(_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def get_log_file_path() -> str:
    """Return the absolute path to the log file."""
    _ensure_log_dir()
    return os.path.abspath(_LOG_FILE)