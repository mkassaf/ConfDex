from __future__ import annotations

import json
import os

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/ollama", tags=["ollama"])

_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


async def _ollama_get(path: str) -> httpx.Response:
    async with httpx.AsyncClient(base_url=_OLLAMA_HOST, timeout=10.0) as client:
        return await client.get(path)


@router.get("/status")
async def ollama_status():
    try:
        r = await _ollama_get("/api/tags")
        r.raise_for_status()
        return {"running": True, "host": _OLLAMA_HOST}
    except Exception:
        return {"running": False, "host": _OLLAMA_HOST}


@router.get("/models")
async def ollama_models():
    try:
        r = await _ollama_get("/api/tags")
        r.raise_for_status()
        data = r.json()
        models = [m["name"] for m in data.get("models", [])]
        return {"models": models}
    except Exception:
        return {"models": [], "error": "Ollama not reachable"}


@router.post("/pull")
async def ollama_pull(body: dict):
    model_name: str = body.get("model", "")
    if not model_name:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="model name required")

    async def _stream():
        async with httpx.AsyncClient(base_url=_OLLAMA_HOST, timeout=600.0) as client:
            async with client.stream(
                "POST", "/api/pull", json={"name": model_name, "stream": True}
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        yield f"data: {line}\n\n"
        yield "data: {\"status\":\"done\"}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")
