from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class UAVRegistrationRequest(BaseModel):
    """Request payload to register a new UAV / engine digital twin."""
    model_config = ConfigDict(extra="forbid")

    uav_id: str = Field(..., description="Unique UAV identifier (e.g. 'UAV-001')", min_length=1)
    engine_id: str = Field(default="ENG-DEFAULT", description="Engine identifier / serial")
    model_type: str = Field(default="piston", description="Engine model class ('piston')")
    configuration: dict[str, Any] = Field(default_factory=dict, description="Optional engine parameters")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata tags, mission name, etc.")


class UAVResponse(BaseModel):
    """UAV digital twin registration and status record."""
    model_config = ConfigDict(extra="forbid")

    uav_id: str
    engine_id: str
    model_type: str
    created_at: datetime
    status: str = "active"
    telemetry_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class UAVListResponse(BaseModel):
    """List of currently registered UAVs."""
    model_config = ConfigDict(extra="forbid")

    total: int
    uavs: list[UAVResponse]
