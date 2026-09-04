from __future__ import annotations

import math

from sih.dt.core.state import EngineState
from sih.dt.models.base import EngineModel
from sih.dt.telemetry.schema import Telemetry


class PistonEngineModel(EngineModel):

    def __init__(
        self,
        base_torque_nm: float = 160.0,
        max_rpm: float = 5200.0,
        ideal_egt_c: float = 700.0,
        ideal_cht_c: float = 180.0,
        low_oil_pressure_psi: float = 20.0,
        high_vibration_mm_s: float = 3.0,
        nominal_battery_v: float = 13.8,
    ) -> None:
        self.base_torque_nm = base_torque_nm
        self.max_rpm = max_rpm
        self.ideal_egt_c = ideal_egt_c
        self.ideal_cht_c = ideal_cht_c
        self.low_oil_pressure_psi = low_oil_pressure_psi
        self.high_vibration_mm_s = high_vibration_mm_s
        self.nominal_battery_v = nominal_battery_v
        self._state = EngineState()

    def _clamp(self, value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
        return max(minimum, min(maximum, value))

    def update(self, telemetry: Telemetry, dt: float) -> EngineState:
        if dt < 0:
            raise ValueError("dt must be non-negative")

        angular_velocity = (telemetry.rpm / 60.0) * 2.0 * math.pi

        throttle_ratio = self._clamp(telemetry.throttle / 100.0, 0.0, 1.0)
        map_ratio = self._clamp(telemetry.manifold_absolute_pressure / 100.0, 0.0, 1.0)
        rpm_ratio = self._clamp(telemetry.rpm / self.max_rpm, 0.0, 1.0)

        # Prototype physics: torque is approximated from throttle, inlet pressure, and RPM.
        torque = self.base_torque_nm * (0.25 + throttle_ratio * 0.9 + map_ratio * 0.55) * (0.35 + rpm_ratio * 0.85)

        # Prototype physics: power is torque multiplied by angular velocity.
        power_w = torque * angular_velocity

        # Prototype physics: engine load increases with throttle and MAP, then modestly with RPM.
        engine_load = self._clamp(
            throttle_ratio * 55.0 + map_ratio * 30.0 + rpm_ratio * 20.0,
            0.0,
            100.0,
        )

        # Prototype physics: fuel efficiency is an approximate inverse of fuel flow at the observed power.
        fuel_flow = max(telemetry.fuel_flow, 1e-6)
        fuel_efficiency = self._clamp((power_w / fuel_flow) * 0.12, 0.0, 100.0)

        # Thermal health drops progressively when EGT/CHT exceed prototype healthy bands.
        egt_abnormality = max(0.0, telemetry.egt - self.ideal_egt_c) / 250.0
        cht_abnormality = max(0.0, telemetry.cht - self.ideal_cht_c) / 140.0
        thermal_health = self._clamp(100.0 - (egt_abnormality + cht_abnormality) * 100.0, 0.0, 100.0)

        # Lubrication health drops when oil pressure is low or oil is excessively hot.
        oil_pressure_health = 100.0
        if telemetry.oil_pressure < self.low_oil_pressure_psi:
            oil_pressure_health -= (self.low_oil_pressure_psi - telemetry.oil_pressure) * 4.0
        oil_temperature_health = 100.0 - max(0.0, telemetry.oil_temperature - 110.0) * 1.5
        lubrication_health = self._clamp(min(oil_pressure_health, oil_temperature_health), 0.0, 100.0)

        # Mechanical health drops with vibration level.
        mechanical_health = self._clamp(100.0 - max(0.0, telemetry.vibration - 1.0) * 35.0, 0.0, 100.0)

        # Electrical health drops if battery voltage is below nominal.
        electrical_delta = self.nominal_battery_v - telemetry.battery_voltage
        electrical_health = self._clamp(100.0 - max(0.0, electrical_delta) * 20.0, 0.0, 100.0)

        # Combustion health is a coarse proxy based on temperature and fuel delivery balance.
        combustion_pressure = max(0.0, telemetry.manifold_absolute_pressure - 40.0) / 60.0
        combustion_health = self._clamp(
            100.0
            - (egt_abnormality * 60.0)
            - (cht_abnormality * 35.0)
            - max(0.0, telemetry.fuel_flow - 20.0) * 1.4
            + combustion_pressure * 10.0,
            0.0,
            100.0,
        )

        # Overall health is the average of the tracked sub-health values.
        overall_health = self._clamp(
            (
                combustion_health
                + thermal_health
                + lubrication_health
                + mechanical_health
                + electrical_health
            )
            / 5.0,
            0.0,
            100.0,
        )

        state = EngineState(
            timestamp=telemetry.timestamp,
            rpm=telemetry.rpm,
            throttle=telemetry.throttle,
            manifold_absolute_pressure=telemetry.manifold_absolute_pressure,
            egt=telemetry.egt,
            cht=telemetry.cht,
            intake_air_temperature=telemetry.intake_air_temperature,
            ambient_temperature=telemetry.ambient_temperature,
            oil_pressure=telemetry.oil_pressure,
            oil_temperature=telemetry.oil_temperature,
            fuel_flow=telemetry.fuel_flow,
            vibration=telemetry.vibration,
            ambient_pressure=telemetry.ambient_pressure,
            battery_voltage=telemetry.battery_voltage,
            estimated_torque=torque,
            estimated_power=power_w,
            engine_load=engine_load,
            fuel_efficiency=fuel_efficiency,
            combustion_health=combustion_health,
            thermal_health=thermal_health,
            lubrication_health=lubrication_health,
            mechanical_health=mechanical_health,
            electrical_health=electrical_health,
            overall_health=overall_health,
        )
        self._state = state
        return state

    def reset(self) -> None:
        self._state = EngineState()

    def get_state(self) -> EngineState:
        return self._state
