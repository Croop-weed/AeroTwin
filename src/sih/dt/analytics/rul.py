from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from sih.dt.core.state import EngineState


class RULStatus(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NOT_TRAINED = "NOT_TRAINED"
    AVAILABLE = "AVAILABLE"


class RULPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: RULStatus
    estimated_remaining_time: float | None = Field(default=None, ge=0.0)
    confidence: float = Field(ge=0.0, le=1.0)
    lower_bound: float | None = Field(default=None, ge=0.0)
    upper_bound: float | None = Field(default=None, ge=0.0)
    timestamp: datetime | None = None


class RULPredictor(Protocol):
    def predict(self, states: Sequence[EngineState]) -> RULPrediction:
        """Predict remaining time without coupling callers to a RUL algorithm."""


class UnavailableRULPredictor:
    """Honest placeholder until run-to-failure data and a trained model exist."""

    def predict(self, states: Sequence[EngineState]) -> RULPrediction:
        timestamp = states[-1].timestamp if states else None
        status = RULStatus.INSUFFICIENT_DATA if not states else RULStatus.NOT_TRAINED
        return RULPrediction(status=status, confidence=0.0, timestamp=timestamp)
