from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ServerHealthResponse(BaseModel):
    """API server health, distinguishing backend process health from UAV engine health."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="ok", description="Server operational status (e.g. 'ok')")
    service: str = Field(default="AeroTwin Digital Twin API", description="Service name")
    version: str = Field(default="0.1.0", description="API version")
    models_ready: bool = Field(default=False, description="Whether ML models are loaded and ready")
    active_uavs: int = Field(default=0, description="Count of active UAV digital twins registered")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusMessageResponse(BaseModel):
    """Generic status and acknowledgement response."""
    model_config = ConfigDict(extra="forbid")

    status: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    model_config = ConfigDict(extra="forbid")

    detail: str
    error_code: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
