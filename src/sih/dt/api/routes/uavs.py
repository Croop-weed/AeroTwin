from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from sih.dt.api.dependencies import StateManagerDep
from sih.dt.api.schemas.common import StatusMessageResponse
from sih.dt.api.schemas.uav import UAVListResponse, UAVRegistrationRequest, UAVResponse

router = APIRouter(prefix="/api/v1/uavs", tags=["UAV Registry"])


@router.post(
    "",
    response_model=UAVResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new UAV / Engine Digital Twin",
)
async def register_uav(
    request: UAVRegistrationRequest,
    state_manager: StateManagerDep,
) -> UAVResponse:
    if state_manager.exists(request.uav_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"UAV with ID '{request.uav_id}' is already registered.",
        )

    record = state_manager.register_uav(
        uav_id=request.uav_id,
        engine_id=request.engine_id,
        model_type=request.model_type,
        configuration=request.configuration,
        metadata=request.metadata,
    )
    return UAVResponse(
        uav_id=record.uav_id,
        engine_id=record.engine_id,
        model_type=record.model_type,
        created_at=record.created_at,
        status="active",
        telemetry_count=record.telemetry_count,
        metadata=record.metadata,
    )


@router.get(
    "",
    response_model=UAVListResponse,
    summary="List all registered UAVs",
)
async def list_uavs(state_manager: StateManagerDep) -> UAVListResponse:
    records = state_manager.list_uavs()
    uavs = [
        UAVResponse(
            uav_id=r.uav_id,
            engine_id=r.engine_id,
            model_type=r.model_type,
            created_at=r.created_at,
            status="active",
            telemetry_count=r.telemetry_count,
            metadata=r.metadata,
        )
        for r in records
    ]
    return UAVListResponse(total=len(uavs), uavs=uavs)


@router.get(
    "/{uav_id}",
    response_model=UAVResponse,
    summary="Get registration details for a specific UAV",
)
async def get_uav(
    uav_id: str,
    state_manager: StateManagerDep,
) -> UAVResponse:
    record = state_manager.get_uav(uav_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"UAV '{uav_id}' not found.",
        )
    return UAVResponse(
        uav_id=record.uav_id,
        engine_id=record.engine_id,
        model_type=record.model_type,
        created_at=record.created_at,
        status="active",
        telemetry_count=record.telemetry_count,
        metadata=record.metadata,
    )


@router.delete(
    "/{uav_id}",
    response_model=StatusMessageResponse,
    summary="Unregister and remove a UAV Digital Twin",
)
async def delete_uav(
    uav_id: str,
    state_manager: StateManagerDep,
) -> StatusMessageResponse:
    deleted = state_manager.delete_uav(uav_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"UAV '{uav_id}' not found.",
        )
    return StatusMessageResponse(
        status="success",
        message=f"UAV '{uav_id}' and all associated states have been successfully removed.",
    )
