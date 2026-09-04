from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from sih.dt.analytics.anomaly import AnomalyResult
from sih.dt.analytics.degradation import DegradationState
from sih.dt.analytics.diagnosis import FaultDiagnosis
from sih.dt.analytics.rul import RULPrediction
from sih.dt.analytics.sensor import SensorStatus


class AnalyticsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anomaly: AnomalyResult | None = None
    fault_diagnoses: list[FaultDiagnosis] = Field(default_factory=list)
    sensor_statuses: list[SensorStatus] = Field(default_factory=list)
    degradation: DegradationState | None = None
    rul: RULPrediction | None = None
    timestamp: datetime | None = None
