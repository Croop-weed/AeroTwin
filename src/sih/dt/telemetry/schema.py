from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Telemetry(BaseModel):


    model_config = ConfigDict(extra="forbid")

    timestamp: datetime

    rpm: float = Field(ge=0, description="Engine speed in revolutions per minute (RPM).")
    throttle: float = Field(ge=0, le=100, description="Throttle position in percent (0-100).")
    manifold_absolute_pressure: float = Field(
        ge=0,
        description="Manifold absolute pressure in kPa (prototype measurement).",
    )
    egt: float = Field(ge=0, description="Exhaust gas temperature in degC.")
    cht: float = Field(ge=0, description="Cylinder head temperature in degC.")
    intake_air_temperature: float = Field(ge=0, description="Intake air temperature in degC.")
    ambient_temperature: float = Field(ge=0, description="Ambient air temperature in degC.")
    oil_pressure: float = Field(ge=0, description="Engine oil pressure in psi.")
    oil_temperature: float = Field(ge=0, description="Engine oil temperature in degC.")
    fuel_flow: float = Field(ge=0, description="Fuel flow in L/h (prototype).")
    injection_timing_deg: float = Field(
        default=0.0,
        ge=0,
        description="Prototype injection timing representation in degrees.",
    )
    vibration: float = Field(ge=0, description="Vibration amplitude in mm/s (prototype).")
    ambient_pressure: float = Field(ge=0, description="Ambient pressure in kPa.")
    battery_voltage: float = Field(ge=0, description="Battery voltage in V.")