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


@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
