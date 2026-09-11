from __future__ import annotations

import logging
from typing import Any

from sih.dt.api.schemas.simulation import (
    SimulationFaultRequest,
    SimulationStartRequest,
    SimulationStatusResponse,
    SimulationStepRequest,
    SimulationThrottleRequest,
)
from sih.dt.api.services.twin_service import TwinService, get_twin_service
from sih.dt.api.state.manager import TwinStateManager, get_state_manager
from sih.dt.simulation.engine import SyntheticEngineSimulator
from sih.dt.simulation.faults import FaultInjector, FaultType
from sih.dt.telemetry.schema import Telemetry

logger = logging.getLogger(__name__)


class SimulationService:
    """Manages synthetic engine simulation sessions, fault injection, and telemetry forwarding."""

    def __init__(
        self,
        state_manager: TwinStateManager | None = None,
        twin_service: TwinService | None = None,
    ) -> None:
        self.state_manager = state_manager or get_state_manager()
        self.twin_service = twin_service or get_twin_service()

    def start_simulation(self, uav_id: str, request: SimulationStartRequest) -> SimulationStatusResponse:
        uav = self.state_manager.get_or_create(uav_id)
        with uav.lock:
            uav.simulator = SyntheticEngineSimulator(
                throttle=request.throttle,
                ambient_temperature=request.ambient_temperature,
                ambient_pressure=request.ambient_pressure,
            )
            uav.fault_injector.clear()
            init_telemetry = uav.simulator.reset()
            return SimulationStatusResponse(
                uav_id=uav_id,
                is_active=True,
                throttle=request.throttle,
                active_fault=None,
                simulated_time_seconds=uav.simulator._time_seconds,
                latest_telemetry=init_telemetry.model_dump(mode="json"),
            )

    def step_simulation(
        self,
        uav_id: str,
        request: SimulationStepRequest,
    ) -> tuple[Telemetry, Any]:
        """Steps the simulator, injects active faults, and optionally processes through the Digital Twin."""
        uav = self.state_manager.get_or_create(uav_id)

        with uav.lock:
            raw_telemetry = uav.simulator.step(request.dt)
            injected_telemetry = uav.fault_injector.inject(raw_telemetry)

        dashboard_snapshot = None
        if request.auto_ingest:
            _, _, dashboard_snapshot = self.twin_service.process_telemetry(uav_id, injected_telemetry)

        return injected_telemetry, dashboard_snapshot

    def set_throttle(self, uav_id: str, request: SimulationThrottleRequest) -> SimulationStatusResponse:
        uav = self.state_manager.get_or_create(uav_id)
        with uav.lock:
            uav.simulator.set_throttle(request.throttle)
            return self._get_status_locked(uav)

    def set_fault(self, uav_id: str, request: SimulationFaultRequest) -> SimulationStatusResponse:
        uav = self.state_manager.get_or_create(uav_id)
        fault_enum: FaultType | None = None
        if request.fault_type and request.fault_type.upper() != "NONE":
            try:
                fault_enum = FaultType[request.fault_type.upper()]
            except KeyError:
                valid_types = [f.name for f in FaultType]
                raise ValueError(
                    f"Unknown fault type '{request.fault_type}'. Valid types are: {', '.join(valid_types)}"
                )

        with uav.lock:
            uav.fault_injector.set_fault(fault_enum)
            return self._get_status_locked(uav)

    def reset_simulation(self, uav_id: str) -> SimulationStatusResponse:
        uav = self.state_manager.get_or_create(uav_id)
        with uav.lock:
            uav.fault_injector.clear()
            init_telemetry = uav.simulator.reset()
            uav.twin.reset()
            uav.states_buffer.clear()
            uav.residual_history.clear()
            return SimulationStatusResponse(
                uav_id=uav_id,
                is_active=True,
                throttle=uav.simulator._throttle,
                active_fault=None,
                simulated_time_seconds=0.0,
                latest_telemetry=init_telemetry.model_dump(mode="json"),
            )

    def get_simulation_status(self, uav_id: str) -> SimulationStatusResponse:
        uav = self.state_manager.get_or_create(uav_id)
        with uav.lock:
            return self._get_status_locked(uav)

    def _get_status_locked(self, uav: Any) -> SimulationStatusResponse:
        active_fault_str = uav.fault_injector.active_fault.value if uav.fault_injector.active_fault else None
        return SimulationStatusResponse(
            uav_id=uav.uav_id,
            is_active=True,
            throttle=uav.simulator._throttle,
            active_fault=active_fault_str,
            simulated_time_seconds=uav.simulator._time_seconds,
            latest_telemetry=None,
        )


_GLOBAL_SIMULATION_SERVICE: SimulationService | None = None


def get_simulation_service() -> SimulationService:
    global _GLOBAL_SIMULATION_SERVICE
    if _GLOBAL_SIMULATION_SERVICE is None:
        _GLOBAL_SIMULATION_SERVICE = SimulationService()
    return _GLOBAL_SIMULATION_SERVICE
