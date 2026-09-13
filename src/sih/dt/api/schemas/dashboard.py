from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from sih.dt.api.schemas.analytics import (
    AnomalyResponse,
    DegradationResponse,
    FaultDiagnosisItem,
    RULResponse,
    SensorStatusItem,
)
from sih.dt.api.schemas.engine import (
    EngineMeasurementsResponse,
    EnginePerformanceResponse,
    EngineTemporalRatesResponse,
    OperatingConditionsResponse,
    SubsystemHealthResponse,
)


class DashboardUAVInfo(BaseModel):
    """UAV / engine metadata for dashboard header."""
    model_config = ConfigDict(extra="forbid")

    uav_id: str
    engine_id: str
    status: str = "active"
    model_type: str = "piston"


class DashboardAnalytics(BaseModel):
    """Analytics section for the dashboard snapshot."""
    model_config = ConfigDict(extra="forbid")

    anomaly: AnomalyResponse
    faults: list[FaultDiagnosisItem] = Field(default_factory=list)
    degradation: DegradationResponse
    rul: RULResponse
    sensors: list[SensorStatusItem] = Field(default_factory=list)


class DashboardSnapshotResponse(BaseModel):
    """Single consolidated, frontend-ready snapshot for Section B Dashboard."""
    model_config = ConfigDict(extra="forbid")

    uav: DashboardUAVInfo
    timestamp: datetime
    engine: EngineMeasurementsResponse
    performance: EnginePerformanceResponse
    temporal: EngineTemporalRatesResponse
    health: SubsystemHealthResponse
    analytics: DashboardAnalytics
    operating_conditions: OperatingConditionsResponse

