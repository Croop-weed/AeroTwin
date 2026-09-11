from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status

from sih.dt.api.dependencies import StateManagerDep
from sih.dt.api.schemas.history import HistoryPoint, HistoryResponse

router = APIRouter(prefix="/api/v1/uavs", tags=["History & Time Series"])


@router.get(
    "/{uav_id}/history",
    response_model=HistoryResponse,
    summary="Get timestamped state and analytics history",
    description="Returns time-series history points suitable for plotting real-time charts in the dashboard.",
)
async def get_history(
    uav_id: str,
    state_manager: StateManagerDep,
    limit: int = Query(default=100, ge=1, le=1000, description="Max history points to return"),
    start_time: datetime | None = Query(default=None, description="Optional start time filter"),
    end_time: datetime | None = Query(default=None, description="Optional end time filter"),
) -> HistoryResponse:
    uav = state_manager.get_uav(uav_id)
    if uav is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"UAV '{uav_id}' not found.",
        )

    with uav.lock:
        raw_points = list(uav.history)

    # Filter by timestamps if provided
    filtered = []
    for item in raw_points:
        ts = item["timestamp"]
        if start_time and ts < start_time:
            continue
        if end_time and ts > end_time:
            continue
        filtered.append(HistoryPoint(**item))

    # Slice up to limit from the tail (most recent)
    result_points = filtered[-limit:]

    return HistoryResponse(
        uav_id=uav_id,
        total_points=len(result_points),
        points=result_points,
    )
