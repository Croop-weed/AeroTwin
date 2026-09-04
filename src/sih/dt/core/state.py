from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class EngineState(BaseModel):
   

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime | None = None

    rpm: float = 0.0
    previous_rpm: float = 0.0
    rpm_rate: float = 0.0
    throttle: float = 0.0
    manifold_absolute_pressure: float = 0.0
    egt: float = 0.0
    egt_rate: float = 0.0
    cht: float = 0.0
    cht_rate: float = 0.0
    intake_air_temperature: float = 0.0
    ambient_temperature: float = 0.0
    oil_pressure: float = 0.0
    oil_temperature: float = 0.0
    oil_temperature_rate: float = 0.0
    fuel_flow: float = 0.0
    vibration: float = 0.0
    vibration_rate: float = 0.0
    ambient_pressure: float = 0.0
    battery_voltage: float = 0.0
    operating_time_seconds: float = 0.0

    estimated_torque: float = 0.0
    estimated_power: float = 0.0
    engine_load: float = 0.0
    fuel_efficiency: float = 0.0
    combustion_health: float = 100.0
    thermal_health: float = 100.0
    lubrication_health: float = 100.0
    mechanical_health: float = 100.0
    electrical_health: float = 100.0
    overall_health: float = 100.0

    def clamp_0_100(self, value: float) -> float:
        return max(0.0, min(100.0, value))
