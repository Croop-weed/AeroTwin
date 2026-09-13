from __future__ import annotations

import math
from datetime import datetime, timezone

from sih.dt.telemetry.schema import Telemetry


class SyntheticEngineSimulator:
    """Simple prototype telemetry simulator for a generic fuel-injected piston engine.

    This is intentionally a demo generator: it produces plausible, smooth telemetry for
    the digital twin without claiming real engine calibration or thermodynamic fidelity.
    """

    def __init__(
        self,
        throttle: float = 25.0,
        ambient_temperature: float = 22.0,
        ambient_pressure: float = 101.3,
    ) -> None:
        self._throttle = 0.0
        self._ambient_temperature = float(ambient_temperature)
        self._ambient_pressure = float(ambient_pressure)
        self._time_seconds = 0.0
        self._rpm = 0.0
        self._manifold_absolute_pressure = 0.0
        self._egt = 0.0
        self._cht = 0.0
        self._intake_air_temperature = 0.0
        self._oil_pressure = 0.0
        self._oil_temperature = 0.0
        self._fuel_flow = 0.0
        self._injection_timing_deg = 0.0
        self._vibration = 0.0
        self._battery_voltage = 0.0
        self.set_throttle(throttle)
        self._initial_throttle = self._throttle
        self.reset()

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def set_throttle(self, throttle: float) -> None:
        self._throttle = self._clamp(float(throttle), 0.0, 100.0)

    def reset(self) -> Telemetry:
        self._time_seconds = 0.0
        self._throttle = self._initial_throttle
        self._rpm = 850.0
        self._manifold_absolute_pressure = 42.0
        self._egt = 610.0
        self._cht = 155.0
        self._intake_air_temperature = self._ambient_temperature + 2.0
        self._oil_pressure = 34.0
        self._oil_temperature = 82.0
        self._fuel_flow = 9.0
        self._vibration = 0.9
        self._battery_voltage = 13.8
        return self.step(0.0)

    def step(self, dt: float) -> Telemetry:
        if dt < 0:
            raise ValueError("dt must be non-negative")

        self._time_seconds += float(dt)

        throttle_ratio = self._throttle / 100.0
        load_factor = throttle_ratio * 0.9 + 0.15

        # Prototype demo relationships: higher throttle generally raises RPM/load/fuel flow.
        rpm_target = 780.0 + self._throttle * 34.0
        self._rpm += (rpm_target - self._rpm) * min(1.0, 0.5 * dt + 0.15)

        manifold_target = 30.0 + self._throttle * 0.6 + 18.0 * load_factor
        self._manifold_absolute_pressure += (manifold_target - self._manifold_absolute_pressure) * min(1.0, 0.6 * dt + 0.2)

        # Higher load generally raises thermal stress and fuel consumption.
        thermal_bias = 0.7 * self._throttle + 25.0 * load_factor
        variation = 12.0 * math.sin(self._time_seconds * 0.9 + 0.25)
        self._egt += (560.0 + thermal_bias + variation - self._egt) * min(1.0, 0.5 * dt + 0.12)
        self._cht += (135.0 + thermal_bias * 0.8 + variation * 0.5 - self._cht) * min(1.0, 0.5 * dt + 0.12)

        intake_variation = 3.0 * math.sin(self._time_seconds * 0.7 + 1.1)
        self._intake_air_temperature += (
            self._ambient_temperature + 2.0 + intake_variation - self._intake_air_temperature
        ) * min(1.0, 0.3 * dt + 0.1)

        # Oil pressure stays plausible during normal engine operation.
        oil_pressure_target = 32.0 + self._throttle * 0.18 + (self._rpm / 100.0) * 0.9
        self._oil_pressure += (oil_pressure_target - self._oil_pressure) * min(1.0, 0.7 * dt + 0.2)

        self._oil_temperature += (
            78.0 + self._throttle * 0.24 + 0.05 * self._rpm / 10.0 - self._oil_temperature
        ) * min(1.0, 0.35 * dt + 0.1)

        fuel_flow_target = 6.0 + self._throttle * 0.32 + self._rpm * 0.0032
        self._fuel_flow += (fuel_flow_target - self._fuel_flow) * min(1.0, 0.6 * dt + 0.2)

        # Vibration varies slightly under load, but remains in a small, reasonable range.
        vibration_wave = 0.5 * math.sin(self._time_seconds * 1.7 + 0.6)
        self._vibration += (
            (0.8 + self._throttle * 0.016 + abs(vibration_wave)) - self._vibration
        ) * min(1.0, 0.5 * dt + 0.15)

        # Battery voltage remains near a normal operating value with gentle variation.
        voltage_wave = 0.18 * math.sin(self._time_seconds * 1.3 + 1.8)
        self._battery_voltage += ((13.8 + voltage_wave) - self._battery_voltage) * min(1.0, 0.4 * dt + 0.1)

        self._rpm = max(0.0, self._rpm)
        self._manifold_absolute_pressure = max(0.0, self._manifold_absolute_pressure)
        self._egt = max(0.0, self._egt)
        self._cht = max(0.0, self._cht)
        self._intake_air_temperature = max(0.0, self._intake_air_temperature)
        self._oil_pressure = max(0.0, self._oil_pressure)
        self._oil_temperature = max(0.0, self._oil_temperature)
        self._fuel_flow = max(0.0, self._fuel_flow)
        self._vibration = max(0.0, self._vibration)
        self._battery_voltage = max(0.0, self._battery_voltage)

        return Telemetry(
            timestamp=datetime.now(timezone.utc),
            rpm=self._rpm,
            throttle=self._throttle,
            manifold_absolute_pressure=self._manifold_absolute_pressure,
            egt=self._egt,
            cht=self._cht,
            intake_air_temperature=self._intake_air_temperature,
            ambient_temperature=self._ambient_temperature,
            oil_pressure=self._oil_pressure,
            oil_temperature=self._oil_temperature,
            fuel_flow=self._fuel_flow,
            injection_timing_deg=self._injection_timing_deg,
            vibration=self._vibration,
            ambient_pressure=self._ambient_pressure,
            battery_voltage=self._battery_voltage,
        )
