from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from sih.dt.api.dependencies import StateManagerDep, TwinServiceDep
from sih.dt.api.schemas.engine import EngineStateResponse

router = APIRouter(prefix="/api/v1/uavs", tags=["Engine State"])


@router.get(
    "/{uav_id}/state",
    response_model=EngineStateResponse,
    summary="Get latest EngineState for a UAV",
    description="Retrieves the full latest calculated EngineState including measurements, performance, and health.",
)
async def get_engine_state(
    uav_id: str,
    state_manager: StateManagerDep,
    twin_service: TwinServiceDep,
) -> EngineStateResponse:
    if not state_manager.exists(uav_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"UAV '{uav_id}' not found.",
        )

    state = twin_service.get_latest_state(uav_id)
    return EngineStateResponse.from_engine_state(uav_id=uav_id, state=state)
