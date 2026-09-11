from __future__ import annotations

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from sih.dt.api.main import app
from sih.dt.api.state.manager import get_state_manager


@pytest.fixture
def clean_state():
    """Ensures state manager is reset before each test."""
    manager = get_state_manager()
    manager.clear()
    yield manager
    manager.clear()


@pytest.fixture
def client(clean_state):
    """FastAPI TestClient with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_telemetry_dict():
    """Valid telemetry dictionary payload."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
        "injection_timing_deg": 0.0,
        "vibration": 1.2,
        "ambient_pressure": 101.3,
        "battery_voltage": 13.8,
    }


@pytest.fixture
def registered_uav(client):
    """Pre-registered UAV fixture."""
    res = client.post(
        "/api/v1/uavs",
        json={
            "uav_id": "UAV-TEST-001",
            "engine_id": "ENG-ROTAX-01",
            "model_type": "piston",
            "metadata": {"mission": "recon_alpha"},
        },
    )
    assert res.status_code == 201
    return "UAV-TEST-001"
