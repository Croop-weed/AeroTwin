from __future__ import annotations

from abc import ABC, abstractmethod

from sih.dt.core.state import EngineState
from sih.dt.telemetry.schema import Telemetry


class EngineModel(ABC):

    @abstractmethod
    def update(self, telemetry: Telemetry, dt: float) -> EngineState:
        """Consume telemetry and return the current engine state."""

    @abstractmethod
    def reset(self) -> None:
        """Reset the model to a known default state."""

    @abstractmethod
    def get_state(self) -> EngineState:
        """Return the current internal engine state."""
