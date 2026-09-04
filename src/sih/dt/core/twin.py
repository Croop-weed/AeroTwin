from __future__ import annotations

from sih.dt.core.state import EngineState
from sih.dt.models.base import EngineModel
from sih.dt.models.piston import PistonEngineModel
from sih.dt.telemetry.schema import Telemetry


class DigitalTwin:

    def __init__(self, model: EngineModel | None = None) -> None:
        self.model = model or PistonEngineModel()
        self._last_telemetry: Telemetry | None = None
        self._state = EngineState()

    def ingest(self, telemetry: Telemetry) -> Telemetry:
        self._last_telemetry = telemetry
        return telemetry

    def update(self, dt: float) -> EngineState:
        if self._last_telemetry is None:
            raise ValueError("No telemetry has been ingested yet.")

        state = self.model.update(self._last_telemetry, dt)
        self._state = state
        return state

    def get_state(self) -> EngineState:
        if self._state is not None and self._state.rpm != 0.0:
            return self._state
        return self.model.get_state()

    def reset(self) -> None:
        self.model.reset()
        self._last_telemetry = None
        self._state = EngineState()
