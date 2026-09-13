from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class SimulationStartRequest(BaseModel):
    """Parameters to start / configure a synthetic engine simulation."""
    model_config = ConfigDict(extra="forbid")

    throttle: float = Field(default=25.0, ge=0, le=100, description="Initial throttle percentage (0-100)")
    ambient_temperature: float = Field(default=22.0, description="Ambient air temperature in degC")
    ambient_pressure: float = Field(default=101.3, description="Ambient atmospheric pressure in kPa")


class SimulationStepRequest(BaseModel):
    """Parameters to advance the simulation."""
    model_config = ConfigDict(extra="forbid")

    dt: float = Field(default=0.1, gt=0, le=60.0, description="Time step in seconds (dt > 0)")
    auto_ingest: bool = Field(
        default=True,
        description="Whether to automatically ingest stepped telemetry into the digital twin"
    )


class SimulationThrottleRequest(BaseModel):
    """Update simulation throttle setting."""
    model_config = ConfigDict(extra="forbid")

    throttle: float = Field(..., ge=0, le=100, description="New throttle percentage (0-100)")


class SimulationFaultRequest(BaseModel):
    """Inject or clear a synthetic fault scenario."""
    model_config = ConfigDict(extra="forbid")

    fault_type: str | None = Field(
        default=None,
        description=(
            "Fault to inject (e.g. 'OVERHEATING', 'LUBRICATION_FAILURE', 'INJECTOR_DEGRADATION', "
            "'MISFIRE', 'COMBUSTION_INSTABILITY', 'ABNORMAL_VIBRATION', 'SENSOR_DRIFT', 'SENSOR_FAILURE'). "
            "Pass null or 'NONE' to clear active fault."
        )
    )


class SimulationStatusResponse(BaseModel):
    """Current state of the simulation engine."""
    model_config = ConfigDict(extra="forbid")

    uav_id: str
    is_active: bool
    throttle: float
    active_fault: str | None
    simulated_time_seconds: float
    latest_telemetry: dict[str, Any] | None = None
