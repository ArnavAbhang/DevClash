"""
main.py
~~~~~~~
Unified FastAPI application — single backend replacing both the Node.js
Express server and the original Python-only FastAPI server.

All routes:
  /api/auth/*    — authentication (register, login, me)
  /api/tasks/*   — task CRUD
  /api/health    — health check
  /summarize     — LLM text summarisation
  /transcribe    — speech-to-text with FFmpeg conversion
  /*             — React SPA (production only, when static/ is built)
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.config import settings
from core.database import close_db, connect_db
from routers.ai import router as ai_router
from routers.auth import router as auth_router
from routers.tasks import router as tasks_router


# ---------------------------------------------------------------------------
# Lifespan — database connect / disconnect
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Tools + Task Manager API",
    version="2.0.0",
    description="Unified FastAPI backend — auth, tasks, ASR, summarisation.",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — development only
# In production the frontend is served by this same process (same origin).
# ---------------------------------------------------------------------------

if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.client_origin,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ---------------------------------------------------------------------------
# API routers  (registered BEFORE the static-file catch-all)
# ---------------------------------------------------------------------------

app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(ai_router)


@app.get("/api/health", tags=["health"])
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ---------------------------------------------------------------------------
# Static file serving — production only
# Vite build outputs to backend/static/ (configured in vite.config.js).
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parent / settings.static_dir
_assets_dir = _STATIC_DIR / "assets"
_index_html = _STATIC_DIR / "index.html"
_frontend_built = _assets_dir.is_dir() and _index_html.is_file()

if _frontend_built:
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        candidate = (_STATIC_DIR / full_path).resolve()
        try:
            candidate.relative_to(_STATIC_DIR.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid path.")
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_index_html)