from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class MissionEvent(BaseModel):
    """Timestamped event occurred during the UAV mission."""
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    event_type: str = Field(..., description="EVENT type: MISSION_START, NORMAL, ANOMALY, FAULT, RECOVERY, etc.")
    description: str
    severity: str = Field(default="INFO", description="INFO, WARNING, or CRITICAL")
    details: dict[str, Any] = Field(default_factory=dict)


class MissionReportResponse(BaseModel):
    """Mission-wise health and operational summary for Section B requirements."""
    model_config = ConfigDict(extra="forbid")

    mission_id: str
    uav_id: str
    engine_id: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_seconds: float = 0.0
    operating_time_seconds: float = 0.0
    total_telemetry_points: int = 0
    average_health: float = 100.0
    min_health: float = 100.0
    max_health: float = 100.0
    anomalies_detected: int = 0
    fault_events_count: int = 0
    active_fault: str | None = None
    degradation_trend: str = "STABLE"
    current_degradation_index: float = 0.0
    maintenance_advisory: str = "System Nominal. No maintenance action required."
    timeline_events: list[MissionEvent] = Field(default_factory=list)
