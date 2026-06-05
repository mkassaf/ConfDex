from __future__ import annotations

import asyncio
import base64
import logging
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from confscraper.web import db as job_db
from confscraper.web import session as session_store
from confscraper.web.routes import auth as auth_router
from confscraper.web.routes import jobs as jobs_router
from confscraper.web.routes import llm as llm_router
from confscraper.web.routes import ollama as ollama_router
from confscraper.web.runner import get_active_jobs, run_job

logger = logging.getLogger(__name__)

WATCHDOG_INTERVAL = 60  # seconds between stuck-job checks

_STATIC_DIR = Path(__file__).parent / "static"


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """The login endpoint accepts HTTP Basic Auth and issues a session cookie.
    Every other endpoint authenticates via session cookie only — Basic Auth headers
    are intentionally ignored elsewhere so browsers that proactively re-send stored
    credentials cannot bypass a logout."""

    async def dispatch(self, request: Request, call_next):
        password = os.environ.get("ADMIN_PASSWORD", "").strip()

        if not password:
            request.state.authenticated = True
            return await call_next(request)

        username = os.environ.get("ADMIN_USERNAME", "admin").strip()

        if request.url.path == "/api/auth/login":
            # Only the login path accepts Basic Auth credentials
            authenticated = False
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Basic "):
                try:
                    decoded = base64.b64decode(auth[6:]).decode("utf-8")
                    provided_user, provided_pass = decoded.split(":", 1)
                    user_ok = secrets.compare_digest(provided_user.encode(), username.encode())
                    pass_ok = secrets.compare_digest(provided_pass.encode(), password.encode())
                    authenticated = user_ok and pass_ok
                except Exception:
                    pass

            if not authenticated:
                return Response(
                    content="Unauthorized",
                    status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="ConfDex"'},
                )
            request.state.authenticated = True
        else:
            # All other endpoints: session cookie is the only valid credential
            cookie_token = request.cookies.get(session_store.SESSION_COOKIE, "")
            request.state.authenticated = session_store.valid(cookie_token)

        return await call_next(request)


def create_app(db_path: Path = Path("confdex.db")) -> FastAPI:
    job_db.set_db_path(db_path)

    app = FastAPI(title="ConfDex", version="0.1.0", docs_url="/api/docs")
    app.add_middleware(BasicAuthMiddleware)

    @app.on_event("startup")
    async def _startup():
        await job_db.init_db()

        # Recover any jobs that were incomplete when the server last stopped
        incomplete = await job_db.list_incomplete_jobs()
        if incomplete:
            logger.info("Recovering %d incomplete job(s) from previous session", len(incomplete))
            for job in incomplete:
                asyncio.create_task(run_job(job["id"]))

        # Start watchdog that re-queues stuck jobs every WATCHDOG_INTERVAL seconds
        asyncio.create_task(_watchdog())

    async def _watchdog():
        while True:
            await asyncio.sleep(WATCHDOG_INTERVAL)
            try:
                active = get_active_jobs()
                incomplete = await job_db.list_incomplete_jobs()
                stuck = [j for j in incomplete if j["id"] not in active]
                for job in stuck:
                    logger.warning("Watchdog: re-queuing stuck job %s (status=%s)", job["id"], job["status"])
                    asyncio.create_task(run_job(job["id"]))
            except Exception:
                logger.exception("Watchdog error")

    app.include_router(auth_router.router)
    app.include_router(jobs_router.router)
    app.include_router(llm_router.router)
    app.include_router(ollama_router.router)

    # Serve built React SPA if the frontend has been built
    _assets_dir = _STATIC_DIR / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(_request: Request, full_path: str):
            file = _STATIC_DIR / full_path
            if file.is_file():
                return FileResponse(file)
            return FileResponse(_STATIC_DIR / "index.html")
    else:
        @app.get("/", include_in_schema=False)
        async def root():
            return {
                "message": "ConfDex API running. Visit /api/docs for the API.",
                "hint": "Build the frontend: cd frontend && npm run build",
            }

    return app
