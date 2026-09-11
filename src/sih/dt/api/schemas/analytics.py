from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class AnomalyResponse(BaseModel):
    """Anomaly detection output."""
    model_config = ConfigDict(extra="forbid")

    is_anomaly: bool
    score: float
    confidence: float = 1.0
    timestamp: datetime | None = None


class FaultDiagnosisItem(BaseModel):
    """Diagnosed fault item."""
    model_config = ConfigDict(extra="forbid")

    fault_type: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: float = Field(..., ge=0.0, le=1.0)
    evidence: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


class DegradationResponse(BaseModel):
    """Degradation index and trend."""
    model_config = ConfigDict(extra="forbid")

    degradation_index: float = Field(..., ge=0.0, le=1.0, description="0=healthy, 1=severely degraded")
    confidence: float = Field(..., ge=0.0, le=1.0)
    trend: str = Field(..., description="STABLE, IMPROVING, WORSENING, or INSUFFICIENT_DATA")
    timestamp: datetime | None = None


class RULResponse(BaseModel):
    """Remaining useful life prediction output."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., description="AVAILABLE, INSUFFICIENT_DATA, NOT_TRAINED, or UNAVAILABLE")
    remaining_useful_life: float | None = Field(default=None, description="Predicted remaining useful life cycles/time")
    lower_bound: float | None = Field(default=None, description="Lower confidence bound")
    upper_bound: float | None = Field(default=None, description="Upper confidence bound")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime | None = None


class SensorStatusItem(BaseModel):
    """Status assessment for an individual sensor."""
    model_config = ConfigDict(extra="forbid")

    sensor_name: str
    status: str = Field(..., description="NORMAL, DRIFT, STUCK, or UNKNOWN")
    confidence: float = Field(..., ge=0.0, le=1.0)
    anomaly_score: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime | None = None


class AnalyticsSummaryResponse(BaseModel):
    """Comprehensive analytics response bundle."""
    model_config = ConfigDict(extra="forbid")

    uav_id: str
    timestamp: datetime | None = None
    anomaly: AnomalyResponse
    faults: list[FaultDiagnosisItem] = Field(default_factory=list)
    degradation: DegradationResponse
    rul: RULResponse
    sensors: list[SensorStatusItem] = Field(default_factory=list)
