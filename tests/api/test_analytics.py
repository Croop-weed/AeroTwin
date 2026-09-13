from __future__ import annotations


def test_analytics_endpoints(client, registered_uav, sample_telemetry_dict):
    # Ingest baseline telemetry
    client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=sample_telemetry_dict)

    # 1. Full bundle
    res_all = client.get(f"/api/v1/uavs/{registered_uav}/analytics")
    assert res_all.status_code == 200
    data = res_all.json()
    assert "anomaly" in data
    assert "faults" in data
    assert "degradation" in data
    assert "rul" in data
    assert "sensors" in data

    # 2. Anomaly
    res_anom = client.get(f"/api/v1/uavs/{registered_uav}/analytics/anomaly")
    assert res_anom.status_code == 200
    anom = res_anom.json()
    assert "is_anomaly" in anom
    assert "score" in anom
    assert isinstance(anom["is_anomaly"], bool)

    # 3. Ad-hoc Anomaly POST
    res_adhoc = client.post(f"/api/v1/uavs/{registered_uav}/analytics/anomaly", json=sample_telemetry_dict)
    assert res_adhoc.status_code == 200
    assert "is_anomaly" in res_adhoc.json()

    # 4. Faults
    res_faults = client.get(f"/api/v1/uavs/{registered_uav}/faults")
    assert res_faults.status_code == 200
    assert isinstance(res_faults.json(), list)

    # 5. RUL
    res_rul = client.get(f"/api/v1/uavs/{registered_uav}/analytics/rul")
    assert res_rul.status_code == 200
    rul = res_rul.json()
    assert "status" in rul
    # Must not invent an RUL value if insufficient data / not ready
    assert rul["status"] in ["AVAILABLE", "INSUFFICIENT_DATA", "NOT_TRAINED", "UNAVAILABLE"]

    # 6. Degradation
    res_deg = client.get(f"/api/v1/uavs/{registered_uav}/analytics/degradation")
    assert res_deg.status_code == 200
    deg = res_deg.json()
    assert "degradation_index" in deg
    assert 0.0 <= deg["degradation_index"] <= 1.0
    assert "trend" in deg

    # 7. Sensors
    res_sensors = client.get(f"/api/v1/uavs/{registered_uav}/analytics/sensors")
    assert res_sensors.status_code == 200
    sensors = res_sensors.json()
    assert isinstance(sensors, list)
    sensor_names = [s["sensor_name"] for s in sensors]
    assert "egt" in sensor_names
    assert "oil_pressure" in sensor_names


def test_fault_diagnosis_structured_evidence(client, registered_uav, sample_telemetry_dict):
    """Verifies that diagnosed faults contain fault_type, confidence, severity, and evidence."""
    # Inject overheating telemetry
    hot_telem = dict(sample_telemetry_dict)
    hot_telem["cht"] = 230.0
    hot_telem["egt"] = 780.0
    client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=hot_telem)

    res = client.get(f"/api/v1/uavs/{registered_uav}/faults")
    assert res.status_code == 200
    faults = res.json()
    assert len(faults) > 0

    for f in faults:
        assert "fault_type" in f
        assert 0.0 <= f["confidence"] <= 1.0
        assert 0.0 <= f["severity"] <= 1.0
        assert isinstance(f["evidence"], dict)
        assert "timestamp" in f


def test_sensor_failure_diagnosis(client, registered_uav, sample_telemetry_dict):
    """Verifies SENSOR_FAILURE diagnosis on battery_voltage loss."""
    failed_telem = dict(sample_telemetry_dict)
    failed_telem["battery_voltage"] = 0.0
    client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=failed_telem)

    res = client.get(f"/api/v1/uavs/{registered_uav}/faults")
    assert res.status_code == 200
    fault_types = [f["fault_type"] for f in res.json()]
    assert "SENSOR_FAILURE" in fault_types

