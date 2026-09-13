from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter

from sih.dt.api.dependencies import AnalyticsServiceDep, StateManagerDep
from sih.dt.api.schemas.common import ServerHealthResponse

router = APIRouter(tags=["System Health"])


@router.get(
    "/",
    summary="API Root Information",
    description="Returns metadata about AeroTwin API service.",
)
async def root():
    return {
        "service": "AeroTwin Digital Twin API",
        "status": "online",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/health",
    response_model=ServerHealthResponse,
    summary="API Server Health Check",
    description="Verifies that the backend API process is healthy and reports ML model readiness.",
)
async def health(
    state_manager: StateManagerDep,
    analytics_service: AnalyticsServiceDep,
) -> ServerHealthResponse:
    return ServerHealthResponse(
        status="ok",
        service="AeroTwin Digital Twin API",
        version="0.1.0",
        models_ready=analytics_service.is_ready,
        active_uavs=state_manager.count(),
        timestamp=datetime.now(timezone.utc),
    )
