from __future__ import annotations

import os

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
async def get_auth_status(request: Request) -> dict:
    """Return whether the user is authenticated and whether auth is configured."""
    return {
        "authenticated": getattr(request.state, "authenticated", True),
        "auth_required": bool(os.environ.get("ADMIN_PASSWORD", "").strip()),
    }


@router.get("/login")
async def login(request: Request):
    """Triggers HTTP Basic Auth (middleware handles the 401 challenge), then redirects to the app."""
    return RedirectResponse(url="/", status_code=302)
