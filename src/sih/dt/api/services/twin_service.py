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


from sih.dt.api.schemas.mission import MissionEvent, MissionReportResponse
from sih.dt.api.schemas.performance import PerformanceMapResponse, PerformanceOperatingPoint
from sih.dt.models.piston import PistonEngineModel

_ENVELOPE_MODEL = PistonEngineModel()


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
                "performance": {
                    "estimated_torque": state.estimated_torque,
                    "estimated_power": state.estimated_power,
                    "engine_load": state.engine_load,
                    "fuel_efficiency": state.fuel_efficiency,
                    "operating_time_seconds": state.operating_time_seconds,
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

    def get_mission_report(self, uav_id: str) -> MissionReportResponse:
        """Computes comprehensive mission-wise health analysis from recorded telemetry history."""
        uav = self.state_manager.get_uav(uav_id)
        if uav is None:
            raise KeyError(f"UAV '{uav_id}' not found.")

        with uav.lock:
            history = list(uav.history)
            latest_state = uav.latest_state
            analytics = uav.latest_analytics

        mission_id = (
            uav.metadata.get("mission")
            or uav.metadata.get("mission_id")
            or f"MSN-{uav.uav_id}-ALPHA"
        )

        if not history:
            now = datetime.now(timezone.utc)
            return MissionReportResponse(
                mission_id=mission_id,
                uav_id=uav.uav_id,
                engine_id=uav.engine_id,
                start_time=uav.created_at,
                end_time=now,
                duration_seconds=0.0,
                operating_time_seconds=0.0,
                total_telemetry_points=0,
                average_health=100.0,
                min_health=100.0,
                max_health=100.0,
                anomalies_detected=0,
                fault_events_count=0,
                active_fault=None,
                degradation_trend="STABLE",
                current_degradation_index=0.0,
                maintenance_advisory="System Nominal. Digital Twin standing by for telemetry feed.",
                timeline_events=[
                    MissionEvent(
                        timestamp=uav.created_at,
                        event_type="MISSION_START",
                        description=f"Digital Twin telemetry session initiated for {uav.uav_id}.",
                        severity="INFO",
                    )
                ],
            )

        start_time = history[0]["timestamp"]
        end_time = history[-1]["timestamp"]
        duration = max(0.0, (end_time - start_time).total_seconds()) if start_time and end_time else 0.0

        health_values = [h["overall_health"] for h in history if "overall_health" in h]
        avg_health = sum(health_values) / len(health_values) if health_values else 100.0
        min_health = min(health_values) if health_values else 100.0
        max_health = max(health_values) if health_values else 100.0

        anomalies_detected = sum(1 for h in history if h.get("is_anomaly"))

        events: list[MissionEvent] = [
            MissionEvent(
                timestamp=start_time,
                event_type="MISSION_START",
                description=f"Flight telemetry transmission began for UAV {uav.uav_id}.",
                severity="INFO",
            )
        ]

        prev_fault = None
        prev_anom = False
        fault_count = 0

        for pt in history:
            ts = pt["timestamp"]
            fault = pt.get("active_fault")
            is_anom = pt.get("is_anomaly", False)

            if fault != prev_fault:
                if fault:
                    fault_count += 1
                    events.append(
                        MissionEvent(
                            timestamp=ts,
                            event_type="FAULT",
                            description=f"Engine fault injected/detected: {fault}",
                            severity="CRITICAL" if any(k in fault for k in ["FAILURE", "OVERHEATING"]) else "WARNING",
                            details={"fault": fault, "health": pt.get("overall_health")},
                        )
                    )
                elif prev_fault is not None:
                    events.append(
                        MissionEvent(
                            timestamp=ts,
                            event_type="RECOVERY",
                            description=f"Fault cleared. Telemetry and health returning to nominal envelope.",
                            severity="INFO",
                            details={"cleared_fault": prev_fault},
                        )
                    )
                prev_fault = fault

            if is_anom and not prev_anom:
                events.append(
                    MissionEvent(
                        timestamp=ts,
                        event_type="ANOMALY",
                        description=f"Anomaly detector flagged residual divergence (score: {pt.get('anomaly_score', 0.0):.2f})",
                        severity="WARNING",
                        details={"score": pt.get("anomaly_score")},
                    )
                )
            prev_anom = is_anom

        current_fault = prev_fault
        deg_trend = "STABLE"
        deg_idx = 0.0
        if analytics:
            deg = analytics.get("degradation", {})
            deg_trend = deg.get("trend", "STABLE")
            deg_idx = deg.get("degradation_index", 0.0)

        # Generate rule-based maintenance advisory
        if current_fault == "OVERHEATING":
            advisory = "CRITICAL: Severe thermal stress detected. Inspect cooling airflow, radiators, and cylinder head assemblies."
        elif current_fault == "LUBRICATION_FAILURE":
            advisory = "CRITICAL: Oil pressure drop detected. Inspect oil pump, lines, and oil filter for metal debris."
        elif current_fault == "INJECTOR_DEGRADATION":
            advisory = "WARNING: Fuel delivery degradation observed. Schedule fuel injector ultrasonic cleaning and recalibration."
        elif current_fault:
            advisory = f"WARNING: Active fault '{current_fault}'. Schedule propulsion subsystem inspection."
        elif min_health < 75.0:
            advisory = "INSPECT SOON: Subsystem health dropped below 75% during mission. Perform post-flight diagnostic review."
        elif anomalies_detected > 3:
            advisory = "MONITOR: Recurrent telemetry deviations flagged by AI models. Review operating temperature and vibration trends."
        else:
            advisory = "NORMAL: Propulsion parameters nominal. Routine scheduled maintenance interval applies."

        return MissionReportResponse(
            mission_id=mission_id,
            uav_id=uav.uav_id,
            engine_id=uav.engine_id,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=round(duration, 2),
            operating_time_seconds=round(latest_state.operating_time_seconds, 2),
            total_telemetry_points=len(history),
            average_health=round(avg_health, 2),
            min_health=round(min_health, 2),
            max_health=round(max_health, 2),
            anomalies_detected=anomalies_detected,
            fault_events_count=fault_count,
            active_fault=current_fault,
            degradation_trend=deg_trend,
            current_degradation_index=round(deg_idx, 3),
            maintenance_advisory=advisory,
            timeline_events=events,
        )

    def get_performance_map(self, uav_id: str) -> PerformanceMapResponse:
        """Generates the engine performance map combining simulated physical envelope and real observed points."""
        uav = self.state_manager.get_uav(uav_id)
        if uav is None:
            raise KeyError(f"UAV '{uav_id}' not found.")

        # 1. Physics-based operating envelope across RPM and Throttle ranges
        envelope_points: list[PerformanceOperatingPoint] = []
        rpms = [1000.0, 1500.0, 2000.0, 2500.0, 3000.0, 3500.0, 4000.0, 4500.0, 5000.0]
        throttles = [15.0, 30.0, 45.0, 60.0, 75.0, 90.0, 100.0]

        temp_model = PistonEngineModel()
        for thr in throttles:
            thr_ratio = thr / 100.0
            load_factor = thr_ratio * 0.9 + 0.15
            map_val = 30.0 + thr * 0.6 + 18.0 * load_factor

            for rpm in rpms:
                fuel_flow = 6.0 + thr * 0.32 + rpm * 0.0032
                synthetic_telemetry = Telemetry(
                    timestamp=datetime.now(timezone.utc),
                    rpm=rpm,
                    throttle=thr,
                    manifold_absolute_pressure=map_val,
                    egt=620.0 + thr * 1.1,
                    cht=145.0 + thr * 0.6,
                    intake_air_temperature=24.0,
                    ambient_temperature=22.0,
                    oil_pressure=32.0 + thr * 0.15 + (rpm / 120.0),
                    oil_temperature=82.0 + thr * 0.2,
                    fuel_flow=fuel_flow,
                    vibration=0.8 + thr * 0.015,
                    ambient_pressure=101.3,
                    battery_voltage=13.8,
                )
                state = temp_model.update(synthetic_telemetry, dt=0.5)
                envelope_points.append(
                    PerformanceOperatingPoint(
                        rpm=round(rpm, 1),
                        throttle=round(thr, 1),
                        engine_load=round(state.engine_load, 1),
                        torque_nm=round(state.estimated_torque, 2),
                        power_kw=round(state.estimated_power / 1000.0, 2),
                        fuel_flow=round(state.fuel_flow, 2),
                        fuel_efficiency=round(state.fuel_efficiency, 2),
                    )
                )

        # 2. Extract observed points from UAV history
        with uav.lock:
            history = list(uav.history)
            latest = uav.latest_state

        observed: list[PerformanceOperatingPoint] = []
        # Sample every Nth point if history is large to keep payload snappy
        step = max(1, len(history) // 50)
        for pt in history[::step]:
            m = pt.get("measurements", {})
            p = pt.get("performance", {})
            if m.get("rpm") is not None:
                observed.append(
                    PerformanceOperatingPoint(
                        rpm=round(m.get("rpm", 0.0), 1),
                        throttle=round(m.get("throttle", 0.0), 1),
                        engine_load=round(p.get("engine_load", 0.0), 1),
                        torque_nm=round(p.get("estimated_torque", 0.0), 2),
                        power_kw=round(p.get("estimated_power", 0.0) / 1000.0, 2),
                        fuel_flow=round(m.get("fuel_flow", 0.0), 2),
                        fuel_efficiency=round(p.get("fuel_efficiency", 0.0), 2),
                    )
                )

        # 3. Current active operating point
        current_point = None
        if latest.rpm > 0.0:
            current_point = PerformanceOperatingPoint(
                rpm=round(latest.rpm, 1),
                throttle=round(latest.throttle, 1),
                engine_load=round(latest.engine_load, 1),
                torque_nm=round(latest.estimated_torque, 2),
                power_kw=round(latest.estimated_power / 1000.0, 2),
                fuel_flow=round(latest.fuel_flow, 2),
                fuel_efficiency=round(latest.fuel_efficiency, 2),
            )

        return PerformanceMapResponse(
            uav_id=uav.uav_id,
            engine_id=uav.engine_id,
            envelope_grid=envelope_points,
            observed_points=observed,
            current_point=current_point,
        )

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
