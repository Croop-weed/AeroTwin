from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from sih.dt.core.state import EngineState


class DegradationTrend(str, Enum):
    STABLE = "STABLE"
    IMPROVING = "IMPROVING"
    WORSENING = "WORSENING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class DegradationState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    degradation_index: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    trend: DegradationTrend
    timestamp: datetime | None = None


class DegradationEstimator(Protocol):
    def estimate(self, states: Sequence[EngineState]) -> DegradationState:
        """Estimate normalized degradation from an EngineState window."""


class BaselineDegradationEstimator:
    """Transparent health-based prototype, not a calibrated degradation model."""

    def estimate(self, states: Sequence[EngineState]) -> DegradationState:
        timestamp = states[-1].timestamp if states else None
        if not states:
            return DegradationState(
                degradation_index=0.0,
                confidence=0.0,
                trend=DegradationTrend.INSUFFICIENT_DATA,
                timestamp=timestamp,
            )
        indices = [max(0.0, min(1.0, 1.0 - state.overall_health / 100.0)) for state in states]
        index = indices[-1]
        trend = DegradationTrend.STABLE
        if len(indices) > 1:
            delta = indices[-1] - indices[0]
            if delta > 0.01:
                trend = DegradationTrend.WORSENING
            elif delta < -0.01:
                trend = DegradationTrend.IMPROVING
        return DegradationState(
            degradation_index=index,
            confidence=min(1.0, len(states) / 10.0),
            trend=trend,
            timestamp=timestamp,
        )
