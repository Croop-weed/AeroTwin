"""API Route modules."""

from sih.dt.api.routes.analytics import router as analytics_router
from sih.dt.api.routes.dashboard import router as dashboard_router
from sih.dt.api.routes.engine import router as engine_router
from sih.dt.api.routes.health import router as health_router
from sih.dt.api.routes.history import router as history_router
from sih.dt.api.routes.simulation import router as simulation_router
from sih.dt.api.routes.telemetry import router as telemetry_router
from sih.dt.api.routes.uavs import router as uavs_router
from sih.dt.api.routes.ws import router as ws_router

__all__ = [
    "analytics_router",
    "dashboard_router",
    "engine_router",
    "health_router",
    "history_router",
    "simulation_router",
    "telemetry_router",
    "uavs_router",
    "ws_router",
]
