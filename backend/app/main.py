"""
Main FastAPI Application Entrypoint for VMotion AI.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.routes import router
from app.api.websocket import ws_router
from app.audit.logger import audit_logger
from app.config import settings
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite persistent database (devices, catalog, jobs, audit)
    init_db()
    audit_logger.log_event(
        event_type="CLUSTER_CONNECTED",
        message=f"{settings.APP_NAME} Backend Engine initialized successfully.",
        details={"version": settings.VERSION, "mode": settings.MODE}
    )
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI-Powered Virtual Machine Migration Control Plane with Deterministic Safety Gates and Human-in-the-Loop Governance.",
    lifespan=lifespan
)

import os
from fastapi.staticfiles import StaticFiles

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ws_router)

# Mount frontend production build if enabled and present
frontend_dist_paths = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")),
    os.path.abspath("frontend/dist"),
    os.path.abspath("/app/frontend/dist"),
]
dist_dir = next((p for p in frontend_dist_paths if os.path.exists(p) and os.path.isdir(p)), None)

if settings.SERVE_FRONTEND and dist_dir:
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
