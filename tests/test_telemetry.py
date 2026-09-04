from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from sih.dt.core.twin import DigitalTwin
from sih.dt.models.piston import PistonEngineModel
from sih.dt.simulation.faults import FaultInjector, FaultType
from sih.dt.telemetry.schema import Telemetry


def make_telemetry(**overrides):
    payload = {
        "timestamp": datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc),
        "rpm": 2400.0,
        "throttle": 55.0,
        "manifold_absolute_pressure": 72.0,
        "egt": 720.0,
        "cht": 185.0,
        "intake_air_temperature": 26.0,
        "ambient_temperature": 24.0,
        "oil_pressure": 38.0,
        "oil_temperature": 92.0,
        "fuel_flow": 18.0,
        "vibration": 1.2,
        "ambient_pressure": 101.3,
        "battery_voltage": 13.8,
    }
    payload.update(overrides)
    return Telemetry(**payload)


def test_valid_telemetry_works():
    telemetry = make_telemetry()
    assert telemetry.rpm == 2400.0
    assert telemetry.throttle == 55.0
    assert telemetry.battery_voltage >= 0


def test_invalid_telemetry_is_rejected():
    with pytest.raises(ValidationError):
        make_telemetry(rpm=-10)

    with pytest.raises(ValidationError):
        make_telemetry(throttle=120)

    with pytest.raises(ValidationError):
        make_telemetry(fuel_flow=-1)

    with pytest.raises(ValidationError):
        make_telemetry(battery_voltage=-1)


def test_piston_engine_model_processes_telemetry():
    model = PistonEngineModel()
    telemetry = make_telemetry()
    state = model.update(telemetry, 0.1)

    assert state.rpm == telemetry.rpm
    assert state.estimated_torque > 0
    assert state.estimated_power > 0
    assert 0 <= state.engine_load <= 100
    assert 0 <= state.combustion_health <= 100


def test_digital_twin_produces_engine_state():
    twin = DigitalTwin(PistonEngineModel())
    telemetry = make_telemetry()
    twin.ingest(telemetry)
    state = twin.update(0.5)

    assert isinstance(state, type(twin.get_state()))
    assert state.rpm == telemetry.rpm
    assert state.estimated_power > 0


def test_changing_telemetry_changes_state():
    twin = DigitalTwin(PistonEngineModel())
    first = make_telemetry(rpm=2200, throttle=40)
    second = make_telemetry(rpm=3400, throttle=70)

    twin.ingest(first)
    first_state = twin.update(0.25)

    twin.ingest(second)
    second_state = twin.update(0.25)

    assert first_state.rpm != second_state.rpm
    assert first_state.estimated_torque != second_state.estimated_torque
    assert first_state.estimated_power != second_state.estimated_power

def test_abnormal_conditions_reduce_health():
    twin = DigitalTwin(PistonEngineModel())

    normal = make_telemetry()
    twin.ingest(normal)
    normal_state = twin.update(0.1)

    abnormal = make_telemetry(
        egt=1000,
        cht=240,
        oil_pressure=10,
        vibration=5.0,
        battery_voltage=10.0,
    )

    twin.ingest(abnormal)
    abnormal_state = twin.update(0.1)

    assert abnormal_state.thermal_health < normal_state.thermal_health
    assert abnormal_state.lubrication_health < normal_state.lubrication_health
    assert abnormal_state.mechanical_health < normal_state.mechanical_health
    assert abnormal_state.electrical_health < normal_state.electrical_health
    assert abnormal_state.overall_health < normal_state.overall_health

@pytest.mark.parametrize(
    "rpm, throttle",
    [
        (1000, 20),
        (1500, 30),
        (2000, 40),
        (2400, 55),
        (3000, 70),
        (3500, 90),
    ],
)
def test_engine_parameters(rpm, throttle):
    model = PistonEngineModel()

    telemetry = make_telemetry(
        rpm=rpm,
        throttle=throttle,
    )

    state = model.update(telemetry, 0.1)

    assert state.rpm == rpm
    assert 0 <= state.engine_load <= 100
    assert state.estimated_torque > 0
    assert state.estimated_power > 0

@pytest.mark.parametrize(
    "rpm, throttle",
    [
        (1000, 20),
        (1500, 30),
        (2000, 40),
        (2400, 55),
        (3000, 70),
        (3500, 90),
    ],
)
def test_engine_operating_conditions(rpm, throttle):
    model = PistonEngineModel()

    telemetry = make_telemetry(
        rpm=rpm,
        throttle=throttle,
    )

    state = model.update(telemetry, 0.1)

    assert state.rpm == rpm
    assert 0 <= state.engine_load <= 100
    assert state.estimated_torque > 0
    assert state.estimated_power > 0


def test_fault_injector_keeps_normal_telemetry_unchanged():
    source = make_telemetry()
    injector = FaultInjector()

    result = injector.inject(source)

    assert result == source
    assert result is not source
    assert result.model_dump() == source.model_dump()


def test_overheating_fault_changes_temperature_values():
    source = make_telemetry()
    injector = FaultInjector(FaultType.OVERHEATING)

    result = injector.inject(source)

    assert result.cht > source.cht
    assert result.egt > source.egt
    assert result.oil_temperature > source.oil_temperature
    assert result.timestamp == source.timestamp
    assert result.rpm == source.rpm


def test_lubrication_failure_changes_pressure_temperature_and_vibration():
    source = make_telemetry()
    injector = FaultInjector(FaultType.LUBRICATION_FAILURE)

    result = injector.inject(source)

    assert result.oil_pressure < source.oil_pressure
    assert result.oil_temperature > source.oil_temperature
    assert result.vibration > source.vibration
    assert result.timestamp == source.timestamp


def test_injector_degradation_changes_fuel_flow_egt_and_rpm():
    source = make_telemetry()
    injector = FaultInjector(FaultType.INJECTOR_DEGRADATION)

    result = injector.inject(source)

    assert result.fuel_flow > source.fuel_flow
    assert result.egt > source.egt
    assert result.rpm < source.rpm
    assert result.throttle == source.throttle


def test_fault_injector_clear_returns_to_unchanged_behavior():
    source = make_telemetry()
    injector = FaultInjector(FaultType.OVERHEATING)

    with_fault = injector.inject(source)
    injector.clear()
    without_fault = injector.inject(source)

    assert with_fault.cht > without_fault.cht
    assert without_fault.model_dump() == source.model_dump()


def test_fault_injected_telemetry_stays_valid():
    source = make_telemetry()
    injector = FaultInjector(FaultType.INJECTOR_DEGRADATION)

    result = injector.inject(source)

    Telemetry(**result.model_dump())
    assert result.rpm >= 0
    assert result.throttle >= 0
    assert result.fuel_flow >= 0
    assert result.battery_voltage >= 0
