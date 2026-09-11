from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from sih.dt.core.state import EngineState


class SubsystemHealthResponse(BaseModel):
    """Subsystem health scores (0-100%)."""
    model_config = ConfigDict(extra="forbid")

    overall: float = Field(..., ge=0, le=100)
    combustion: float = Field(..., ge=0, le=100)
    thermal: float = Field(..., ge=0, le=100)
    lubrication: float = Field(..., ge=0, le=100)
    mechanical: float = Field(..., ge=0, le=100)
    electrical: float = Field(..., ge=0, le=100)


class EngineMeasurementsResponse(BaseModel):
    """Raw and processed sensor measurements."""
    model_config = ConfigDict(extra="forbid")

    rpm: float
    throttle: float
    manifold_absolute_pressure: float
    egt: float
    cht: float
    intake_air_temperature: float
    ambient_temperature: float
    oil_pressure: float
    oil_temperature: float
    fuel_flow: float
    injection_timing_deg: float
    vibration: float
    ambient_pressure: float
    battery_voltage: float


class EnginePerformanceResponse(BaseModel):
    """Derived physical engine metrics."""
    model_config = ConfigDict(extra="forbid")

    estimated_torque: float
    estimated_power: float
    engine_load: float
    fuel_efficiency: float
    operating_time_seconds: float


class OperatingConditionsResponse(BaseModel):
    """Normalized operating point ratios."""
    model_config = ConfigDict(extra="forbid")

    rpm_ratio: float
    throttle_ratio: float
    map_ratio: float
    fuel_flow_ratio: float


class EngineTemporalRatesResponse(BaseModel):
    """Temporal rates of change."""
    model_config = ConfigDict(extra="forbid")

    previous_rpm: float
    rpm_rate: float
    egt_rate: float
    cht_rate: float
    oil_temperature_rate: float
    vibration_rate: float


class EngineStateResponse(BaseModel):
    """Complete EngineState representation for a UAV."""
    model_config = ConfigDict(extra="forbid")

    uav_id: str
    timestamp: datetime | None
    measurements: EngineMeasurementsResponse
    performance: EnginePerformanceResponse
    health: SubsystemHealthResponse
    operating_conditions: OperatingConditionsResponse
    temporal_rates: EngineTemporalRatesResponse

    @classmethod
    def from_engine_state(cls, uav_id: str, state: EngineState) -> EngineStateResponse:
        return cls(
            uav_id=uav_id,
            timestamp=state.timestamp,
            measurements=EngineMeasurementsResponse(
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
            health=SubsystemHealthResponse(
                overall=state.overall_health,
                combustion=state.combustion_health,
                thermal=state.thermal_health,
                lubrication=state.lubrication_health,
                mechanical=state.mechanical_health,
                electrical=state.electrical_health,
            ),
            operating_conditions=OperatingConditionsResponse(
                rpm_ratio=state.rpm_ratio,
                throttle_ratio=state.throttle_ratio,
                map_ratio=state.map_ratio,
                fuel_flow_ratio=state.fuel_flow_ratio,
            ),
            temporal_rates=EngineTemporalRatesResponse(
                previous_rpm=state.previous_rpm,
                rpm_rate=state.rpm_rate,
                egt_rate=state.egt_rate,
                cht_rate=state.cht_rate,
                oil_temperature_rate=state.oil_temperature_rate,
                vibration_rate=state.vibration_rate,
            ),
        )
