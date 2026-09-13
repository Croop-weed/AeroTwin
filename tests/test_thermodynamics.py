from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sih.dt.models.piston import PistonEngineModel
from sih.dt.telemetry.schema import Telemetry
from sih.dt.thermodynamics.atmosphere import air_density
from sih.dt.thermodynamics.constants import ThermodynamicConstants
from sih.dt.thermodynamics.model import ThermodynamicModel


def calculate(**overrides):
    values = {
        "manifold_absolute_pressure_kpa": 101.325,
        "intake_air_temperature_c": 15.0,
        "rpm": 2400.0,
        "fuel_flow_l_h": 20.0,
    }
    values.update(overrides)
    return ThermodynamicModel().calculate(**values)


def test_standard_atmospheric_density():
    assert air_density(101325.0, 288.15) == pytest.approx(1.225, rel=0.001)


def test_hotter_intake_air_reduces_density():
    assert calculate(intake_air_temperature_c=50.0).air_density_kg_m3 < calculate().air_density_kg_m3


def test_increased_map_increases_density():
    assert calculate(manifold_absolute_pressure_kpa=120.0).air_density_kg_m3 > calculate().air_density_kg_m3


def test_fuel_flow_converts_from_liters_per_hour():
    constants = ThermodynamicConstants(fuel_density_kg_l=0.8)
    result = ThermodynamicModel(constants).calculate(
        manifold_absolute_pressure_kpa=100.0,
        intake_air_temperature_c=20.0,
        rpm=0.0,
        fuel_flow_l_h=36.0,
    )
    assert result.fuel_mass_flow_kg_s == pytest.approx(0.008)


def test_afr_and_equivalence_ratio():
    result = calculate()
    assert result.air_fuel_ratio == pytest.approx(result.air_mass_flow_kg_s / result.fuel_mass_flow_kg_s)
    assert result.equivalence_ratio == pytest.approx(14.7 / result.air_fuel_ratio)


def test_zero_fuel_has_zero_mixture_ratios():
    result = calculate(fuel_flow_l_h=0.0)
    assert result.air_fuel_ratio == 0.0
    assert result.equivalence_ratio == 0.0


@pytest.mark.parametrize(
    "overrides",
    [
        {"manifold_absolute_pressure_kpa": 0.0},
        {"intake_air_temperature_c": -273.15 - 0.01},
        {"rpm": -1.0},
        {"fuel_flow_l_h": -1.0},
        {"fuel_flow_l_h": float("nan")},
    ],
)
def test_invalid_inputs_are_rejected(overrides):
    with pytest.raises(ValueError):
        calculate(**overrides)


def test_engine_state_contains_thermodynamic_result():
    telemetry = Telemetry(
        timestamp=datetime.now(timezone.utc),
        rpm=2400.0,
        throttle=50.0,
        manifold_absolute_pressure=75.0,
        egt=700.0,
        cht=180.0,
        intake_air_temperature=25.0,
        ambient_temperature=20.0,
        oil_pressure=35.0,
        oil_temperature=90.0,
        fuel_flow=20.0,
        vibration=1.0,
        ambient_pressure=101.3,
        battery_voltage=13.8,
    )
    state = PistonEngineModel().update(telemetry, 0.1)
    assert state.air_density > 0.0
    assert state.air_mass_flow > 0.0
    assert state.fuel_mass_flow > 0.0