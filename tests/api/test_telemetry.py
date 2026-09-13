from __future__ import annotations


def test_telemetry_ingestion_success(client, registered_uav, sample_telemetry_dict):
    res = client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=sample_telemetry_dict)
    assert res.status_code == 200
    data = res.json()
    assert data["uav_id"] == registered_uav
    assert data["status"] == "processed"
    assert "overall_health" in data
    assert 0.0 <= data["overall_health"] <= 100.0


def test_telemetry_validation_rejection(client, registered_uav, sample_telemetry_dict):
    # Negative RPM should fail Pydantic validation (ge=0)
    bad_telemetry = dict(sample_telemetry_dict)
    bad_telemetry["rpm"] = -500.0
    res = client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=bad_telemetry)
    assert res.status_code == 422

    # Throttle > 100 should fail Pydantic validation (le=100)
    bad_throttle = dict(sample_telemetry_dict)
    bad_throttle["throttle"] = 120.0
    res2 = client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=bad_throttle)
    assert res2.status_code == 422

    # Extra fields are rejected (extra="forbid")
    extra_field = dict(sample_telemetry_dict)
    extra_field["unknown_sensor_data"] = 999.0
    res3 = client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=extra_field)
    assert res3.status_code == 422


def test_multi_uav_isolation(client, sample_telemetry_dict):
    # Register two distinct UAVs
    client.post("/api/v1/uavs", json={"uav_id": "UAV-A"})
    client.post("/api/v1/uavs", json={"uav_id": "UAV-B"})

    # Send high RPM telemetry to UAV-A
    telem_a = dict(sample_telemetry_dict)
    telem_a["rpm"] = 3500.0
    client.post("/api/v1/uavs/UAV-A/telemetry", json=telem_a)

    # Send low RPM telemetry to UAV-B
    telem_b = dict(sample_telemetry_dict)
    telem_b["rpm"] = 900.0
    client.post("/api/v1/uavs/UAV-B/telemetry", json=telem_b)

    # Verify states are isolated
    state_a = client.get("/api/v1/uavs/UAV-A/state").json()
    state_b = client.get("/api/v1/uavs/UAV-B/state").json()

    assert state_a["measurements"]["rpm"] == 3500.0
    assert state_b["measurements"]["rpm"] == 900.0
    assert state_a["measurements"]["rpm"] != state_b["measurements"]["rpm"]
