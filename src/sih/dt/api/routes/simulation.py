from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from sih.dt.api.dependencies import BroadcastServiceDep, SimulationServiceDep, StateManagerDep
from sih.dt.api.schemas.dashboard import DashboardSnapshotResponse
from sih.dt.api.schemas.simulation import (
    SimulationFaultRequest,
    SimulationStartRequest,
    SimulationStatusResponse,
    SimulationStepRequest,
    SimulationThrottleRequest,
)

router = APIRouter(prefix="/api/v1/uavs", tags=["Simulation Engine"])


@router.post(
    "/{uav_id}/simulation/start",
    response_model=SimulationStatusResponse,
    summary="Start / initialize synthetic engine simulator",
)
async def start_simulation(
    uav_id: str,
    request: SimulationStartRequest,
    simulation_service: SimulationServiceDep,
) -> SimulationStatusResponse:
    return simulation_service.start_simulation(uav_id, request)


@router.post(
    "/{uav_id}/simulation/step",
    summary="Advance simulation by dt and optionally update Digital Twin",
)
async def step_simulation(
    uav_id: str,
    request: SimulationStepRequest,
    simulation_service: SimulationServiceDep,
    broadcast_service: BroadcastServiceDep,
):
    injected_telemetry, dashboard_snapshot = simulation_service.step_simulation(uav_id, request)

    if dashboard_snapshot is not None:
        await broadcast_service.broadcast_json(uav_id, dashboard_snapshot.model_dump(mode="json"))

    return {
        "uav_id": uav_id,
        "step_dt": request.dt,
        "telemetry": injected_telemetry.model_dump(mode="json"),
        "dashboard_snapshot": dashboard_snapshot.model_dump(mode="json") if dashboard_snapshot else None,
    }


@router.post(
    "/{uav_id}/simulation/throttle",
    response_model=SimulationStatusResponse,
    summary="Set simulation throttle position",
)
async def set_throttle(
    uav_id: str,
    request: SimulationThrottleRequest,
    simulation_service: SimulationServiceDep,
) -> SimulationStatusResponse:
    return simulation_service.set_throttle(uav_id, request)


@router.post(
    "/{uav_id}/simulation/fault",
    response_model=SimulationStatusResponse,
    summary="Inject or clear a synthetic engine fault",
)
async def set_fault(
    uav_id: str,
    request: SimulationFaultRequest,
    simulation_service: SimulationServiceDep,
) -> SimulationStatusResponse:
    try:
        return simulation_service.set_fault(uav_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/{uav_id}/simulation/reset",
    response_model=SimulationStatusResponse,
    summary="Reset simulation and Digital Twin state",
)
async def reset_simulation(
    uav_id: str,
    simulation_service: SimulationServiceDep,
) -> SimulationStatusResponse:
    return simulation_service.reset_simulation(uav_id)


@router.get(
    "/{uav_id}/simulation/state",
    response_model=SimulationStatusResponse,
    summary="Get current simulator state",
)
async def get_simulation_state(
    uav_id: str,
    simulation_service: SimulationServiceDep,
) -> SimulationStatusResponse:
    return simulation_service.get_simulation_status(uav_id)
