from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from sih.dt.api.schemas.engine import EngineMeasurementsResponse, SubsystemHealthResponse


class HistoryPoint(BaseModel):
    """Single time-series point for historical charting."""
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    measurements: EngineMeasurementsResponse
    health: SubsystemHealthResponse
    overall_health: float
    is_anomaly: bool = False
    anomaly_score: float = 0.0
    active_fault: str | None = None
    degradation_index: float = 0.0
    rul_estimate: float | None = None


class HistoryResponse(BaseModel):
    """Historical time-series response."""
    model_config = ConfigDict(extra="forbid")

    uav_id: str
    total_points: int
    points: list[HistoryPoint]
