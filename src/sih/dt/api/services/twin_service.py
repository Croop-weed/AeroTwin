from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from sih.dt.api.schemas.analytics import AnalyticsSummaryResponse
from sih.dt.api.schemas.dashboard import (
    DashboardAnalytics,
    DashboardSnapshotResponse,
    DashboardUAVInfo,
)
from sih.dt.api.schemas.engine import (
    EngineMeasurementsResponse,
    EnginePerformanceResponse,
    EngineStateResponse,
    EngineTemporalRatesResponse,
    OperatingConditionsResponse,
    SubsystemHealthResponse,
)
from sih.dt.api.services.analytics_service import AnalyticsService, get_analytics_service
from sih.dt.api.services.broadcast_service import BroadcastService, get_broadcast_service
from sih.dt.api.state.manager import TwinStateManager, UAVRecord, get_state_manager
from sih.dt.core.state import EngineState
from sih.dt.features.schema import RESIDUAL_CHANNELS
from sih.dt.telemetry.schema import Telemetry

logger = logging.getLogger(__name__)


class TwinService:
    """Coordinates telemetry ingestion, Digital Twin updates, analytics, and history."""

    def __init__(
        self,
        state_manager: TwinStateManager | None = None,
        analytics_service: AnalyticsService | None = None,
        broadcast_service: BroadcastService | None = None,
    ) -> None:
        self.state_manager = state_manager or get_state_manager()
        self.analytics_service = analytics_service or get_analytics_service()
        self.broadcast_service = broadcast_service or get_broadcast_service()

    def process_telemetry(
        self,
        uav_id: str,
        telemetry: Telemetry,
    ) -> tuple[EngineState, AnalyticsSummaryResponse, DashboardSnapshotResponse]:
        """Ingests telemetry into the isolated Digital Twin for uav_id and runs the analytics pipeline."""
        uav = self.state_manager.get_or_create(uav_id)

        with uav.lock:
            # 1. Compute dt
            dt = 0.1
            if uav.last_telemetry_time is not None and telemetry.timestamp is not None:
                delta = (telemetry.timestamp - uav.last_telemetry_time).total_seconds()
                if 0 < delta <= 60.0:
                    dt = delta
            uav.last_telemetry_time = telemetry.timestamp

            # 2. Ingest into DigitalTwin and update
            uav.twin.ingest(telemetry)
            state = uav.twin.update(dt)
            uav.latest_state = state
            uav.telemetry_count += 1
            uav.states_buffer.append(state)

            # 3. Track residuals for RUL model
            expected = self.analytics_service.physics_ref.expected_state(state)
            current_residuals = [
                float(getattr(state, channel, 0.0) - getattr(expected, channel, 0.0))
                for channel in RESIDUAL_CHANNELS
            ]
            uav.residual_history.append(current_residuals)
            if len(uav.residual_history) > 200:
                uav.residual_history = uav.residual_history[-200:]

            # 4. Evaluate Analytics
            analytics = self.analytics_service.evaluate(
                uav_id=uav_id,
                states=list(uav.states_buffer),
                residual_history=uav.residual_history,
            )
            uav.latest_analytics = analytics.model_dump()

            # 5. Construct Dashboard Snapshot
            dashboard_snapshot = self._build_dashboard_snapshot(uav, state, analytics)

            # 6. Record to in-memory History
            history_item = {
                "timestamp": state.timestamp or datetime.now(timezone.utc),
                "measurements": {
                    "rpm": state.rpm,
                    "throttle": state.throttle,
                    "manifold_absolute_pressure": state.manifold_absolute_pressure,
                    "egt": state.egt,
                    "cht": state.cht,
                    "intake_air_temperature": state.intake_air_temperature,
                    "ambient_temperature": state.ambient_temperature,
                    "oil_pressure": state.oil_pressure,
                    "oil_temperature": state.oil_temperature,
                    "fuel_flow": state.fuel_flow,
                    "injection_timing_deg": state.injection_timing_deg,
                    "vibration": state.vibration,
                    "ambient_pressure": state.ambient_pressure,
                    "battery_voltage": state.battery_voltage,
                },
                "health": {
                    "overall": state.overall_health,
                    "combustion": state.combustion_health,
                    "thermal": state.thermal_health,
                    "lubrication": state.lubrication_health,
                    "mechanical": state.mechanical_health,
                    "electrical": state.electrical_health,
                },
                "overall_health": state.overall_health,
                "is_anomaly": analytics.anomaly.is_anomaly,
                "anomaly_score": analytics.anomaly.score,
                "active_fault": analytics.faults[0].fault_type if analytics.faults else None,
                "degradation_index": analytics.degradation.degradation_index,
                "rul_estimate": analytics.rul.remaining_useful_life,
            }
            uav.history.append(history_item)

        return state, analytics, dashboard_snapshot

    def get_latest_state(self, uav_id: str) -> EngineState:
        uav = self.state_manager.get_uav(uav_id)
        if uav is None:
            raise KeyError(f"UAV '{uav_id}' not found.")
        with uav.lock:
            return uav.latest_state

    def get_dashboard_snapshot(self, uav_id: str) -> DashboardSnapshotResponse:
        uav = self.state_manager.get_uav(uav_id)
        if uav is None:
            raise KeyError(f"UAV '{uav_id}' not found.")

        with uav.lock:
            state = uav.latest_state
            if uav.latest_analytics:
                analytics = AnalyticsSummaryResponse(**uav.latest_analytics)
            else:
                analytics = self.analytics_service.evaluate(
                    uav_id=uav_id,
                    states=list(uav.states_buffer),
                    residual_history=uav.residual_history,
                )
            return self._build_dashboard_snapshot(uav, state, analytics)

    def _build_dashboard_snapshot(
        self,
        uav: UAVRecord,
        state: EngineState,
        analytics: AnalyticsSummaryResponse,
    ) -> DashboardSnapshotResponse:
        ts = state.timestamp or datetime.now(timezone.utc)
        return DashboardSnapshotResponse(
            uav=DashboardUAVInfo(
                uav_id=uav.uav_id,
                engine_id=uav.engine_id,
                status="active",
                model_type=uav.model_type,
            ),
            timestamp=ts,
            engine=EngineMeasurementsResponse(
                rpm=state.rpm,
                throttle=state.throttle,
                manifold_absolute_pressure=state.manifold_absolute_pressure,
                egt=state.egt,
                cht=state.cht,
                intake_air_temperature=state.intake_air_temperature,
                ambient_temperature=state.ambient_temperature,
                oil_pressure=state.oil_pressure,
                oil_temperature=state.oil_temperature,
                fuel_flow=state.fuel_flow,
                injection_timing_deg=state.injection_timing_deg,
                vibration=state.vibration,
                ambient_pressure=state.ambient_pressure,
                battery_voltage=state.battery_voltage,
            ),
            performance=EnginePerformanceResponse(
                estimated_torque=state.estimated_torque,
                estimated_power=state.estimated_power,
                engine_load=state.engine_load,
                fuel_efficiency=state.fuel_efficiency,
                operating_time_seconds=state.operating_time_seconds,
            ),
            temporal=EngineTemporalRatesResponse(
                previous_rpm=state.previous_rpm,
                rpm_rate=state.rpm_rate,
                egt_rate=state.egt_rate,
                cht_rate=state.cht_rate,
                oil_temperature_rate=state.oil_temperature_rate,
                vibration_rate=state.vibration_rate,
            ),
            health=SubsystemHealthResponse(
                overall=state.overall_health,
                combustion=state.combustion_health,
                thermal=state.thermal_health,
                lubrication=state.lubrication_health,
                mechanical=state.mechanical_health,
                electrical=state.electrical_health,
            ),
            analytics=DashboardAnalytics(
                anomaly=analytics.anomaly,
                faults=analytics.faults,
                degradation=analytics.degradation,
                rul=analytics.rul,
                sensors=analytics.sensors,
            ),
            operating_conditions=OperatingConditionsResponse(
                rpm_ratio=state.rpm_ratio,
                throttle_ratio=state.throttle_ratio,
                map_ratio=state.map_ratio,
                fuel_flow_ratio=state.fuel_flow_ratio,
            ),
        )


_GLOBAL_TWIN_SERVICE: TwinService | None = None


def get_twin_service() -> TwinService:
    global _GLOBAL_TWIN_SERVICE
    if _GLOBAL_TWIN_SERVICE is None:
        _GLOBAL_TWIN_SERVICE = TwinService()
    return _GLOBAL_TWIN_SERVICE
