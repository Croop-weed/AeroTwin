from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from sih.dt.api.dependencies import StateManagerDep, TwinServiceDep
from sih.dt.api.schemas.dashboard import DashboardSnapshotResponse

router = APIRouter(prefix="/api/v1/uavs", tags=["Dashboard Snapshot"])


@router.get(
    "/{uav_id}/dashboard",
    response_model=DashboardSnapshotResponse,
    summary="Get single-call consolidated dashboard snapshot",
    description=(
        "Consolidated hero endpoint designed specifically for Section B (Visualization & Output Presentation). "
        "Returns the complete snapshot required for the frontend dashboard in a single call: "
        "real-time engine measurements, performance metrics, subsystem health scores, "
        "operating condition ratios, and full analytics (anomaly status, fault diagnoses, "
        "degradation, RUL, and sensor statuses)."
    ),
)
async def get_dashboard_snapshot(
    uav_id: str,
    state_manager: StateManagerDep,
    twin_service: TwinServiceDep,
) -> DashboardSnapshotResponse:
    if not state_manager.exists(uav_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"UAV '{uav_id}' not found.",
        )

    return twin_service.get_dashboard_snapshot(uav_id)
