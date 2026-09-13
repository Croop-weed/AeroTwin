from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from sih.dt.api.dependencies import AnalyticsServiceDep, StateManagerDep
from sih.dt.api.schemas.analytics import (
    AnalyticsSummaryResponse,
    AnomalyResponse,
    DegradationResponse,
    FaultDiagnosisItem,
    RULResponse,
    SensorStatusItem,
)
from sih.dt.api.schemas.telemetry import TelemetryIngestRequest

router = APIRouter(prefix="/api/v1/uavs", tags=["Analytics & AI"])


def _get_uav_or_404(uav_id: str, state_manager: StateManagerDep):
    uav = state_manager.get_uav(uav_id)
    if uav is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"UAV '{uav_id}' not found.",
        )
    return uav


@router.get(
    "/{uav_id}/analytics",
    response_model=AnalyticsSummaryResponse,
    summary="Get full analytics bundle for a UAV",
)
async def get_all_analytics(
    uav_id: str,
    state_manager: StateManagerDep,
    analytics_service: AnalyticsServiceDep,
) -> AnalyticsSummaryResponse:
    uav = _get_uav_or_404(uav_id, state_manager)
    with uav.lock:
        return analytics_service.evaluate(
            uav_id=uav_id,
            states=list(uav.states_buffer),
            residual_history=uav.residual_history,
        )


@router.get(
    "/{uav_id}/analytics/anomaly",
    response_model=AnomalyResponse,
    summary="Get current anomaly detection status",
)
async def get_anomaly_status(
    uav_id: str,
    state_manager: StateManagerDep,
    analytics_service: AnalyticsServiceDep,
) -> AnomalyResponse:
    uav = _get_uav_or_404(uav_id, state_manager)
    with uav.lock:
        analytics = analytics_service.evaluate(
            uav_id=uav_id,
            states=list(uav.states_buffer),
            residual_history=uav.residual_history,
        )
        return analytics.anomaly


@router.post(
    "/{uav_id}/analytics/anomaly",
    response_model=AnomalyResponse,
    summary="Evaluate anomaly status for an ad-hoc telemetry payload",
)
async def evaluate_ad_hoc_anomaly(
    uav_id: str,
    telemetry_req: TelemetryIngestRequest,
    state_manager: StateManagerDep,
    analytics_service: AnalyticsServiceDep,
) -> AnomalyResponse:
    uav = _get_uav_or_404(uav_id, state_manager)
    core_telemetry = telemetry_req.to_telemetry()
    with uav.lock:
        # Clone twin model to test without mutating live state
        state = uav.twin.model.update(core_telemetry, dt=0.1)
        test_states = list(uav.states_buffer) + [state]
        analytics = analytics_service.evaluate(
            uav_id=uav_id,
            states=test_states,
            residual_history=uav.residual_history,
        )
        return analytics.anomaly


@router.get(
    "/{uav_id}/faults",
    response_model=list[FaultDiagnosisItem],
    summary="Get active fault diagnoses and evidence",
)
@router.get(
    "/{uav_id}/analytics/faults",
    response_model=list[FaultDiagnosisItem],
    include_in_schema=False,
)
async def get_faults(
    uav_id: str,
    state_manager: StateManagerDep,
    analytics_service: AnalyticsServiceDep,
) -> list[FaultDiagnosisItem]:
    uav = _get_uav_or_404(uav_id, state_manager)
    with uav.lock:
        analytics = analytics_service.evaluate(
            uav_id=uav_id,
            states=list(uav.states_buffer),
            residual_history=uav.residual_history,
        )
        return analytics.faults


@router.get(
    "/{uav_id}/analytics/rul",
    response_model=RULResponse,
    summary="Get remaining useful life (RUL) estimation",
)
async def get_rul(
    uav_id: str,
    state_manager: StateManagerDep,
    analytics_service: AnalyticsServiceDep,
) -> RULResponse:
    uav = _get_uav_or_404(uav_id, state_manager)
    with uav.lock:
        analytics = analytics_service.evaluate(
            uav_id=uav_id,
            states=list(uav.states_buffer),
            residual_history=uav.residual_history,
        )
        return analytics.rul


@router.get(
    "/{uav_id}/analytics/degradation",
    response_model=DegradationResponse,
    summary="Get engine degradation index and trend",
)
async def get_degradation(
    uav_id: str,
    state_manager: StateManagerDep,
    analytics_service: AnalyticsServiceDep,
) -> DegradationResponse:
    uav = _get_uav_or_404(uav_id, state_manager)
    with uav.lock:
        analytics = analytics_service.evaluate(
            uav_id=uav_id,
            states=list(uav.states_buffer),
            residual_history=uav.residual_history,
        )
        return analytics.degradation


@router.get(
    "/{uav_id}/analytics/sensors",
    response_model=list[SensorStatusItem],
    summary="Get individual sensor health and drift assessment",
)
async def get_sensors(
    uav_id: str,
    state_manager: StateManagerDep,
    analytics_service: AnalyticsServiceDep,
) -> list[SensorStatusItem]:
    uav = _get_uav_or_404(uav_id, state_manager)
    with uav.lock:
        analytics = analytics_service.evaluate(
            uav_id=uav_id,
            states=list(uav.states_buffer),
            residual_history=uav.residual_history,
        )
        return analytics.sensors
