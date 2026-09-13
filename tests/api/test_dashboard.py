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


def test_mission_report_endpoint(client, registered_uav, sample_telemetry_dict):
    # Ingest a sample point
    client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=sample_telemetry_dict)

    res = client.get(f"/api/v1/uavs/{registered_uav}/mission-report")
    assert res.status_code == 200
    report = res.json()

    assert report["uav_id"] == registered_uav
    assert report["total_telemetry_points"] >= 1
    assert "average_health" in report
    assert "min_health" in report
    assert "maintenance_advisory" in report
    assert "timeline_events" in report
    assert len(report["timeline_events"]) >= 1
    assert report["timeline_events"][0]["event_type"] == "MISSION_START"


def test_performance_map_endpoint(client, registered_uav, sample_telemetry_dict):
    # Ingest a sample point
    client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=sample_telemetry_dict)

    res = client.get(f"/api/v1/uavs/{registered_uav}/performance-map")
    assert res.status_code == 200
    pmap = res.json()

    assert pmap["uav_id"] == registered_uav
    assert "envelope_grid" in pmap
    assert len(pmap["envelope_grid"]) > 10
    assert "observed_points" in pmap
    assert len(pmap["observed_points"]) >= 1
    assert pmap["current_point"] is not None
    assert pmap["current_point"]["rpm"] == 2400.0
    assert "disclaimer" in pmap


def test_dashboard_static_page_serves_html(client):
    res = client.get("/dashboard/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "AeroTwin" in res.text
