"""
Groq API client for transcription and intent routing.
"""

import json
from typing import Any

import httpx
from fastapi import HTTPException, status

from src.app.core.config import get_settings


def transcribe_audio(file_bytes: bytes, filename: str = "audio.webm", language: str | None = None) -> str:
    """Send audio bytes to Groq Whisper API and return the transcribed text."""
    settings = get_settings()

    files = {"file": (filename, file_bytes, _infer_mime(filename))}
    data: dict[str, Any] = {"model": settings.groq_transcription_model}
    if language:
        data["language"] = language

    try:
        with httpx.Client(timeout=settings.request_timeout_seconds) as client:
            resp = client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                files=files,
                data=data,
            )
        resp.raise_for_status()
        result = resp.json()
        return result["text"]
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq transcription failed: {exc.response.text}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq transcription request error: {exc}",
        ) from exc


def route_intent(transcription: str) -> dict[str, Any]:
    """Send transcription text to Groq LLM and return structured routing JSON."""
    settings = get_settings()

    system_prompt = (
        "You are a task routing assistant. Your ONLY job is to respond with a valid JSON object "
        "and NOTHING else — no explanations, no greetings, no extra text.\n\n"
        "Available endpoints:\n"
        "- GET /tasks — list all tasks (params: empty object {})\n"
        "- POST /tasks — create a new task (params: {\"title\": \"...\", \"done\": false})\n"
        "- PUT /tasks/{id} — replace a task (params: {\"title\": \"...\", \"done\": true/false})\n"
        "- PATCH /tasks/{id} — partially update a task (params: {\"title\": \"...\"} or {\"done\": true/false})\n"
        "- DELETE /tasks/{id} — delete a task (params: {\"task_id\": <int>})\n\n"
        "Examples:\n"
        'User: "add buy groceries to my list"\n'
        'Response: {"endpoint": "/tasks", "method": "POST", "params": {"title": "Buy groceries"}}\n\n'
        'User: "show all my tasks"\n'
        'Response: {"endpoint": "/tasks", "method": "GET", "params": {}}\n\n'
        'User: "mark task 1 as done"\n'
        'Response: {"endpoint": "/tasks", "method": "PATCH", "params": {"task_id": 1, "done": true}}\n\n'
        'User: "delete task 3"\n'
        'Response: {"endpoint": "/tasks", "method": "DELETE", "params": {"task_id": 3}}\n\n'
        "IMPORTANT: Respond with ONLY the raw JSON object. No markdown, no code fences, no extra words."
    )

    try:
        with httpx.Client(timeout=settings.request_timeout_seconds) as client:
            resp = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.groq_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": transcription},
                    ],
                    "temperature": 0.1,
                },
            )
        resp.raise_for_status()
        result = resp.json()
        content = result["choices"][0]["message"]["content"].strip()

        # --- Extract JSON from anywhere in the LLM response ---
        # Sometimes the LLM adds explanatory text before/after the JSON,
        # or wraps it in markdown fences like ```json ... ```
        
        # Strategy 1: Find markdown code fences (```json ... ``` or ``` ... ```)
        import re
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", content, re.DOTALL)
        if fence_match:
            content = fence_match.group(1).strip()
        
        # Strategy 2: Find a JSON object {...} anywhere in the text
        if not content.startswith("{"):
            json_match = re.search(r"(\{.*\})", content, re.DOTALL)
            if json_match:
                content = json_match.group(1).strip()

        # If we ended up with empty text, use fallback
        if not content:
            return {"endpoint": "/tasks", "method": "GET", "params": {}}

        parsed = json.loads(content)
        return parsed
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq LLM routing failed: {exc.response.text}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq LLM request error: {exc}",
        ) from exc
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to parse Groq LLM response: {exc}. Raw content: '{content}'",
        ) from exc


def _infer_mime(filename: str) -> str:
    """Infer MIME type from filename extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "webm": "audio/webm",
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "mp4": "audio/mp4",
        "ogg": "audio/ogg",
        "m4a": "audio/mp4",
    }.get(ext, "application/octet-stream")