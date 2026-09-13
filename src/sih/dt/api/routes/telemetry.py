from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from sih.dt.api.dependencies import BroadcastServiceDep, StateManagerDep, TwinServiceDep
from sih.dt.api.schemas.telemetry import TelemetryIngestRequest, TelemetryIngestResponse

router = APIRouter(prefix="/api/v1/uavs", tags=["Telemetry Ingestion"])


@router.post(
    "/{uav_id}/telemetry",
    response_model=TelemetryIngestResponse,
    summary="Ingest telemetry for a UAV",
    description=(
        "Ingests a validated telemetry sample into the specified UAV's Digital Twin. "
        "Calculates delta time, computes EngineState, evaluates real-time analytics "
        "(anomaly detection, fault diagnosis, degradation, RUL), stores into history, "
        "and broadcasts updates to connected WebSockets."
    ),
)
async def ingest_telemetry(
    uav_id: str,
    request: TelemetryIngestRequest,
    twin_service: TwinServiceDep,
    broadcast_service: BroadcastServiceDep,
) -> TelemetryIngestResponse:
    try:
        core_telemetry = request.to_telemetry()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Telemetry validation failed: {exc}",
        )

    state, analytics, dashboard_snapshot = twin_service.process_telemetry(uav_id, core_telemetry)

    # Broadcast updated dashboard snapshot to active WebSocket subscribers
    await broadcast_service.broadcast_json(uav_id, dashboard_snapshot.model_dump(mode="json"))

    active_fault = analytics.faults[0].fault_type if analytics.faults else None

    return TelemetryIngestResponse(
        uav_id=uav_id,
        status="processed",
        timestamp=state.timestamp or core_telemetry.timestamp,
        overall_health=state.overall_health,
        is_anomaly=analytics.anomaly.is_anomaly,
        anomaly_score=analytics.anomaly.score,
        active_fault=active_fault,
    )
