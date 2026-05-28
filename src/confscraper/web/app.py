from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from confscraper.web import db as job_db
from confscraper.web.routes import jobs as jobs_router
from confscraper.web.routes import ollama as ollama_router

_STATIC_DIR = Path(__file__).parent / "static"


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Require HTTP Basic Auth when ADMIN_PASSWORD env var is set."""

    async def dispatch(self, request: Request, call_next):
        password = os.environ.get("ADMIN_PASSWORD", "").strip()
        if not password:
            return await call_next(request)

        username = os.environ.get("ADMIN_USERNAME", "admin").strip()

        auth = request.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode("utf-8")
                provided_user, provided_pass = decoded.split(":", 1)
                user_ok = secrets.compare_digest(provided_user.encode(), username.encode())
                pass_ok = secrets.compare_digest(provided_pass.encode(), password.encode())
                if user_ok and pass_ok:
                    return await call_next(request)
            except Exception:
                pass

        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="ConfDex"'},
        )


def create_app(db_path: Path = Path("confdex.db")) -> FastAPI:
    job_db.set_db_path(db_path)

    app = FastAPI(title="ConfDex", version="0.1.0", docs_url="/api/docs")
    app.add_middleware(BasicAuthMiddleware)

    @app.on_event("startup")
    async def _startup():
        await job_db.init_db()

    app.include_router(jobs_router.router)
    app.include_router(ollama_router.router)

    # Serve built React SPA if the frontend has been built
    _assets_dir = _STATIC_DIR / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(_request: Request, full_path: str):  # noqa: ARG001
            return FileResponse(_STATIC_DIR / "index.html")
    else:
        @app.get("/", include_in_schema=False)
        async def root():
            return {
                "message": "ConfDex API running. Visit /api/docs for the API.",
                "hint": "Build the frontend: cd frontend && npm run build",
            }

    return app
