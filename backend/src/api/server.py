"""The FastAPI app: routers, the security middleware, the compiled dashboard.

`create_app()` builds the app without starting anything, so tests can serve
it with no runtime. `backend/src/app.py` (the composition root) opens the
database and starts the runtime around it.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.src.api.routers import account, engines, events, risk, settings, system, trades
from backend.src.api.security import LocalOnlyMiddleware
from backend.src.services.exchange.types import ExchangeError
from backend.src.utils.lifecycle import NotAvailable
from backend.src.utils.os_utils import repo_root
from backend.src.utils.version_history import APP_NAME, __version__

log = logging.getLogger(__name__)

DIST = repo_root() / "frontend" / "dist"


def create_app(lifespan=None) -> FastAPI:
    app = FastAPI(title=APP_NAME, version=__version__, lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.add_middleware(LocalOnlyMiddleware)
    for r in (system, account, engines, trades, risk, events, settings):
        app.include_router(r.router)

    @app.exception_handler(ValueError)
    async def _bad_request(_: Request, exc: ValueError):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(KeyError)
    async def _not_found(_: Request, exc: KeyError):
        return JSONResponse({"detail": f"not found: {exc}"}, status_code=404)

    @app.exception_handler(ExchangeError)
    async def _exchange(_: Request, exc: ExchangeError):
        return JSONResponse({"detail": f"exchange: {exc}"}, status_code=502)

    @app.exception_handler(NotAvailable)
    async def _not_available(_: Request, exc: NotAvailable):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    _mount_dashboard(app, DIST)
    return app


def _mount_dashboard(app: FastAPI, dist: Path) -> None:
    index = dist / "index.html"
    if not index.exists():
        log.warning("[Server] %s missing; run `npm run build` in frontend/", index)
        return
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def _spa(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": "not found"}, status_code=404)
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)
