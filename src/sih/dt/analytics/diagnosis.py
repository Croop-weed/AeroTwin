from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from sih.dt.analytics.anomaly import AnomalyResult
from sih.dt.core.state import EngineState


class FaultType(str, Enum):
    MISFIRE = "MISFIRE"
    INJECTOR_ABNORMALITY = "INJECTOR_ABNORMALITY"
    LUBRICATION_ISSUE = "LUBRICATION_ISSUE"
    SENSOR_DRIFT_OR_FAILURE = "SENSOR_DRIFT_OR_FAILURE"
    COMBUSTION_INSTABILITY = "COMBUSTION_INSTABILITY"
    OVERHEATING = "OVERHEATING"
    ABNORMAL_VIBRATION = "ABNORMAL_VIBRATION"


class FaultDiagnosis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fault_type: FaultType
    confidence: float = Field(ge=0.0, le=1.0)
    severity: float = Field(ge=0.0, le=1.0)
    evidence: dict[str, float | str] = Field(default_factory=dict)
    timestamp: datetime | None = None


class FaultDiagnoser(Protocol):
    def diagnose(
        self,
        states: Sequence[EngineState],
        anomaly: AnomalyResult | None = None,
    ) -> list[FaultDiagnosis]:
        """Diagnose independently of the anomaly detector implementation."""


class BaselineFaultDiagnoser:
    """Small explainable baseline for wiring tests, not a complete fault classifier."""

    def diagnose(
        self,
        states: Sequence[EngineState],
        anomaly: AnomalyResult | None = None,
    ) -> list[FaultDiagnosis]:
        if not states:
            return []
        state = states[-1]
        timestamp = state.timestamp
        candidates: list[tuple[FaultType, float, dict[str, float | str]]] = [
            (
                FaultType.OVERHEATING,
                max(0.0, min(1.0, max(state.egt_rate / 100.0, state.cht_rate / 50.0))),
                {"egt_rate": state.egt_rate, "cht_rate": state.cht_rate},
            ),
            (
                FaultType.LUBRICATION_ISSUE,
                max(0.0, min(1.0, max((20.0 - state.oil_pressure) / 20.0, state.oil_temperature_rate / 50.0))),
                {"oil_pressure": state.oil_pressure, "oil_temperature_rate": state.oil_temperature_rate},
            ),
            (
                FaultType.ABNORMAL_VIBRATION,
                max(0.0, min(1.0, max((state.vibration - 3.0) / 3.0, state.vibration_rate / 5.0))),
                {"vibration": state.vibration, "vibration_rate": state.vibration_rate},
            ),
            (
                FaultType.INJECTOR_ABNORMALITY,
                max(0.0, min(1.0, max(state.fuel_flow_ratio - 0.35, -state.rpm_rate / 5000.0))),
                {"fuel_flow_ratio": state.fuel_flow_ratio, "rpm_rate": state.rpm_rate},
            ),
        ]
        fault_type, score, evidence = max(candidates, key=lambda candidate: candidate[1])
        if anomaly is not None:
            score = max(score, min(1.0, anomaly.score))
        if score <= 0.0:
            return []
        return [
            FaultDiagnosis(
                fault_type=fault_type,
                confidence=score,
                severity=score,
                evidence=evidence,
                timestamp=timestamp,
            )
        ]


__all__ = ["BaselineFaultDiagnoser", "FaultDiagnosis", "FaultDiagnoser", "FaultType"]
