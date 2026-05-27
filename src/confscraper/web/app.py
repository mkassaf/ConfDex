from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from confscraper.web import db as job_db
from confscraper.web.routes import jobs as jobs_router
from confscraper.web.routes import ollama as ollama_router

_STATIC_DIR = Path(__file__).parent / "static"


def create_app(db_path: Path = Path("confdex.db")) -> FastAPI:
    job_db.set_db_path(db_path)

    app = FastAPI(title="ConfDex", version="0.1.0", docs_url="/api/docs")

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
