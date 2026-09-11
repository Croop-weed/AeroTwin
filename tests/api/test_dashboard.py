from __future__ import annotations


def test_dashboard_snapshot_structure(client, registered_uav, sample_telemetry_dict):
    client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=sample_telemetry_dict)

    res = client.get(f"/api/v1/uavs/{registered_uav}/dashboard")
    assert res.status_code == 200
    data = res.json()

    # Verify root sections
    assert "uav" in data
    assert "timestamp" in data
    assert "engine" in data
    assert "performance" in data
    assert "temporal" in data
    assert "health" in data
    assert "analytics" in data
    assert "operating_conditions" in data

    # Verify temporal block
    assert "previous_rpm" in data["temporal"]
    assert "rpm_rate" in data["temporal"]
    assert "egt_rate" in data["temporal"]
    assert "cht_rate" in data["temporal"]

    # Verify uav block
    assert data["uav"]["uav_id"] == registered_uav
    assert data["uav"]["status"] == "active"

    # Verify engine block
    assert data["engine"]["rpm"] == 2400.0
    assert data["engine"]["egt"] == 720.0
    assert data["engine"]["cht"] == 185.0
    assert data["engine"]["oil_pressure"] == 38.0
    assert data["engine"]["vibration"] == 1.2

    # Verify health block
    assert "overall" in data["health"]
    assert "combustion" in data["health"]
    assert "thermal" in data["health"]
    assert "lubrication" in data["health"]
    assert "mechanical" in data["health"]
    assert "electrical" in data["health"]

    # Verify analytics sub-block
    assert "anomaly" in data["analytics"]
    assert "faults" in data["analytics"]
    assert "degradation" in data["analytics"]
    assert "rul" in data["analytics"]
    assert "sensors" in data["analytics"]

    # Verify operating conditions
    assert "rpm_ratio" in data["operating_conditions"]
    assert "throttle_ratio" in data["operating_conditions"]
    assert "map_ratio" in data["operating_conditions"]
    assert "fuel_flow_ratio" in data["operating_conditions"]


def test_dashboard_dynamic_update(client, registered_uav, sample_telemetry_dict):
    # Send normal telemetry
    client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=sample_telemetry_dict)
    snap1 = client.get(f"/api/v1/uavs/{registered_uav}/dashboard").json()
    assert snap1["engine"]["rpm"] == 2400.0

    # Send higher RPM telemetry
    updated = dict(sample_telemetry_dict)
    updated["rpm"] = 3100.0
    client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=updated)

    snap2 = client.get(f"/api/v1/uavs/{registered_uav}/dashboard").json()
    assert snap2["engine"]["rpm"] == 3100.0
