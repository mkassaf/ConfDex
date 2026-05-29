from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter(prefix="/api/llm", tags=["llm"])

_TRACKED_KEYS = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "MISTRAL_API_KEY",
]


@router.get("/env-keys")
async def get_env_keys() -> dict[str, bool]:
    """Return provider key availability and feature flags (boolean only)."""
    result = {key: bool(os.environ.get(key, "").strip()) for key in _TRACKED_KEYS}
    result["DISABLE_OLLAMA"] = os.environ.get("DISABLE_OLLAMA", "false").strip().lower() == "true"
    return result
