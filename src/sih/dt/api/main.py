from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sih.dt.api.routes import (
    analytics_router,
    dashboard_router,
    engine_router,
    health_router,
    history_router,
    simulation_router,
    telemetry_router,
    uavs_router,
    ws_router,
)
from sih.dt.api.services.analytics_service import get_analytics_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sih.dt.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event handler. Loads and warms up AI models once on startup."""
    logger.info("Initializing AeroTwin Digital Twin API lifespan...")
    analytics_service = get_analytics_service()
    analytics_service.initialize_models(fast=True)
    yield
    logger.info("Shutting down AeroTwin Digital Twin API...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AeroTwin Digital Twin API",
        version="0.1.0",
        description=(
            "Production-style REST & WebSocket backend for AeroTwin / SIH Digital Twin. "
            "Exposes multi-UAV engine digital twin states, validated telemetry ingestion, "
            "comprehensive analytics (anomaly detection, fault diagnosis, RUL, degradation, "
            "sensor health), real-time simulation, and single-shot Section B dashboard snapshots."
        ),
        lifespan=lifespan,
    )

    # Keep local development origins explicit while allowing direct browser API access.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global error handlers
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "error_code": "BAD_REQUEST"},
        )

    @app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc).strip("'"), "error_code": "NOT_FOUND"},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        if isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )
        logger.error(f"Unhandled server error on {request.url}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred.", "error_code": "INTERNAL_SERVER_ERROR"},
        )

    # Register API routers
    app.include_router(health_router)
    app.include_router(uavs_router)
    app.include_router(telemetry_router)
    app.include_router(engine_router)
    app.include_router(analytics_router)
    app.include_router(dashboard_router)
    app.include_router(history_router)
    app.include_router(simulation_router)
    app.include_router(ws_router)

    # Mount static frontend dashboard if built
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    frontend_dist = Path(__file__).resolve().parents[4] / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/dashboard", StaticFiles(directory=str(frontend_dist), html=True), name="dashboard")

    return app


app = create_app()

# Triggering backend restart to load new ML caches

# Triggering backend restart to load metric updates
