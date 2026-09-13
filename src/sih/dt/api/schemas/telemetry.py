from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field

from sih.dt.telemetry.schema import Telemetry


class TelemetryIngestRequest(BaseModel):
    """Payload representing a single telemetry sample sent by a UAV or simulation client."""
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime | None = Field(
        default=None,
        description="Sample timestamp. If omitted, current UTC timestamp is used."
    )
    rpm: float = Field(ge=0, description="Engine speed in RPM.")
    throttle: float = Field(ge=0, le=100, description="Throttle position (0-100%).")
    manifold_absolute_pressure: float = Field(ge=0, description="Manifold absolute pressure in kPa.")
    egt: float = Field(ge=0, description="Exhaust gas temperature in degC.")
    cht: float = Field(ge=0, description="Cylinder head temperature in degC.")
    intake_air_temperature: float = Field(ge=0, description="Intake air temperature in degC.")
    ambient_temperature: float = Field(ge=0, description="Ambient temperature in degC.")
    oil_pressure: float = Field(ge=0, description="Oil pressure in psi.")
    oil_temperature: float = Field(ge=0, description="Oil temperature in degC.")
    fuel_flow: float = Field(ge=0, description="Fuel flow in L/h.")
    injection_timing_deg: float = Field(default=0.0, ge=0, description="Injection timing in degrees.")
    vibration: float = Field(ge=0, description="Vibration amplitude in mm/s.")
    ambient_pressure: float = Field(ge=0, description="Ambient pressure in kPa.")
    battery_voltage: float = Field(ge=0, description="Battery voltage in V.")

    def to_telemetry(self) -> Telemetry:
        """Converts to the strict core Telemetry Pydantic model."""
        ts = self.timestamp or datetime.now(timezone.utc)
        return Telemetry(
            timestamp=ts,
            rpm=self.rpm,
            throttle=self.throttle,
            manifold_absolute_pressure=self.manifold_absolute_pressure,
            egt=self.egt,
            cht=self.cht,
            intake_air_temperature=self.intake_air_temperature,
            ambient_temperature=self.ambient_temperature,
            oil_pressure=self.oil_pressure,
            oil_temperature=self.oil_temperature,
            fuel_flow=self.fuel_flow,
            injection_timing_deg=self.injection_timing_deg,
            vibration=self.vibration,
            ambient_pressure=self.ambient_pressure,
            battery_voltage=self.battery_voltage,
        )


class TelemetryIngestResponse(BaseModel):
    """Response after ingesting telemetry and updating the twin."""
    model_config = ConfigDict(extra="forbid")

    uav_id: str
    status: str = "processed"
    timestamp: datetime
    overall_health: float
    is_anomaly: bool = False
    anomaly_score: float = 0.0
    active_fault: str | None = None
