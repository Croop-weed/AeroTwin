from __future__ import annotations


def test_engine_state_retrieval(client, registered_uav, sample_telemetry_dict):
    # Ingest telemetry
    client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=sample_telemetry_dict)

    res = client.get(f"/api/v1/uavs/{registered_uav}/state")
    assert res.status_code == 200
    data = res.json()

    assert data["uav_id"] == registered_uav
    assert "measurements" in data
    assert "performance" in data
    assert "health" in data
    assert "operating_conditions" in data
    assert "temporal_rates" in data

    # Verify specific fields
    assert data["measurements"]["rpm"] == 2400.0
    assert data["measurements"]["throttle"] == 55.0
    assert data["measurements"]["egt"] == 720.0

    # Verify performance calculations
    assert data["performance"]["estimated_torque"] >= 0.0
    assert data["performance"]["estimated_power"] >= 0.0
    assert data["performance"]["engine_load"] >= 0.0

    # Verify subsystem health
    assert 0.0 <= data["health"]["overall"] <= 100.0
    assert 0.0 <= data["health"]["combustion"] <= 100.0
    assert 0.0 <= data["health"]["thermal"] <= 100.0
    assert 0.0 <= data["health"]["lubrication"] <= 100.0
    assert 0.0 <= data["health"]["mechanical"] <= 100.0
    assert 0.0 <= data["health"]["electrical"] <= 100.0
