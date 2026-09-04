from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from sih.dt.core.state import EngineState


class SensorCondition(str, Enum):
    NORMAL = "NORMAL"
    DRIFT = "DRIFT"
    STUCK = "STUCK"
    UNKNOWN = "UNKNOWN"


class SensorStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensor_name: str
    status: SensorCondition
    confidence: float = Field(ge=0.0, le=1.0)
    anomaly_score: float = Field(ge=0.0, le=1.0)
    timestamp: datetime | None = None


class SensorAnomalyDetector(Protocol):
    def inspect(self, states: Sequence[EngineState]) -> list[SensorStatus]:
        """Assess sensor behavior separately from physical engine health."""


class BaselineSensorAnomalyDetector:
    """Minimal temporal sensor check; it does not diagnose engine faults."""

    SENSOR_FIELDS = ("rpm", "egt", "cht", "oil_pressure", "oil_temperature", "fuel_flow", "vibration", "battery_voltage")

    def inspect(self, states: Sequence[EngineState]) -> list[SensorStatus]:
        if not states:
            return [SensorStatus(sensor_name=field, status=SensorCondition.UNKNOWN, confidence=0.0, anomaly_score=0.0) for field in self.SENSOR_FIELDS]
        statuses: list[SensorStatus] = []
        for field in self.SENSOR_FIELDS:
            values = [float(getattr(state, field)) for state in states]
            unique_count = len(set(values))
            status = SensorCondition.NORMAL
            score = 0.0
            if len(values) >= 3 and unique_count == 1:
                status = SensorCondition.STUCK
                score = 1.0
            elif len(values) >= 3 and all(a <= b for a, b in zip(values, values[1:])) and values[-1] != values[0]:
                status = SensorCondition.DRIFT
                score = min(1.0, abs(values[-1] - values[0]) / max(1.0, abs(values[0])))
            statuses.append(
                SensorStatus(
                    sensor_name=field,
                    status=status,
                    confidence=1.0 if len(values) >= 2 else 0.5,
                    anomaly_score=score,
                    timestamp=states[-1].timestamp,
                )
            )
        return statuses
