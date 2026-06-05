from __future__ import annotations

import os

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from confscraper.web import session as session_store

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
    """Triggers HTTP Basic Auth (middleware handles the 401 challenge), then sets a session cookie and redirects."""
    token = session_store.create()
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        session_store.SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout(request: Request):
    """Revoke the session cookie. Returns JSON so the frontend can call this via fetch()."""
    token = request.cookies.get(session_store.SESSION_COOKIE, "")
    if token:
        session_store.revoke(token)
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"ok": True})
    response.delete_cookie(session_store.SESSION_COOKIE)
    return response
