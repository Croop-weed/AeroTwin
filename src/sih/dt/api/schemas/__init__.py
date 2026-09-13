"""API Pydantic Request & Response Schemas."""

from sih.dt.api.schemas.common import ErrorResponse, ServerHealthResponse, StatusMessageResponse
from sih.dt.api.schemas.uav import UAVListResponse, UAVRegistrationRequest, UAVResponse
from sih.dt.api.schemas.telemetry import TelemetryIngestRequest, TelemetryIngestResponse
from sih.dt.api.schemas.engine import EngineStateResponse, SubsystemHealthResponse
from sih.dt.api.schemas.analytics import (
    AnalyticsSummaryResponse,
    AnomalyResponse,
    DegradationResponse,
    FaultDiagnosisItem,
    RULResponse,
    SensorStatusItem,
)
from sih.dt.api.schemas.dashboard import DashboardSnapshotResponse
from sih.dt.api.schemas.history import HistoryPoint, HistoryResponse
from sih.dt.api.schemas.simulation import (
    SimulationFaultRequest,
    SimulationStartRequest,
    SimulationStatusResponse,
    SimulationStepRequest,
    SimulationThrottleRequest,
)

from sih.dt.api.schemas.mission import MissionEvent, MissionReportResponse
from sih.dt.api.schemas.performance import PerformanceMapResponse, PerformanceOperatingPoint

__all__ = [
    "AnalyticsSummaryResponse",
    "AnomalyResponse",
    "DashboardSnapshotResponse",
    "DegradationResponse",
    "EngineStateResponse",
    "ErrorResponse",
    "FaultDiagnosisItem",
    "HistoryPoint",
    "HistoryResponse",
    "MissionEvent",
    "MissionReportResponse",
    "PerformanceMapResponse",
    "PerformanceOperatingPoint",
    "RULResponse",
    "SensorStatusItem",
    "ServerHealthResponse",
    "SimulationFaultRequest",
    "SimulationStartRequest",
    "SimulationStatusResponse",
    "SimulationStepRequest",
    "SimulationThrottleRequest",
    "StatusMessageResponse",
    "SubsystemHealthResponse",
    "TelemetryIngestRequest",
    "TelemetryIngestResponse",
    "UAVListResponse",
    "UAVRegistrationRequest",
    "UAVResponse",
]
