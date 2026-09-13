from __future__ import annotations


def test_e2e_normal_to_fault_transition(client, registered_uav, sample_telemetry_dict):
    """
    End-to-end integration test demonstrating dynamic Digital Twin behavior:
    Normal flight telemetry -> Healthy dashboard
    Fault injection -> Telemetry with fault -> Degraded health, anomaly detected, fault diagnosed.
    """
    # 1. Ingest normal telemetry
    normal_res = client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=sample_telemetry_dict)
    assert normal_res.status_code == 200

    dash_normal = client.get(f"/api/v1/uavs/{registered_uav}/dashboard").json()
    assert dash_normal["health"]["overall"] > 80.0
    assert dash_normal["engine"]["cht"] == 185.0
    assert dash_normal["engine"]["oil_pressure"] == 38.0

    # 2. Start simulation and step normally
    client.post(
        f"/api/v1/uavs/{registered_uav}/simulation/start",
        json={"throttle": 50.0},
    )
    client.post(
        f"/api/v1/uavs/{registered_uav}/simulation/step",
        json={"dt": 0.5, "auto_ingest": True},
    )
    dash_sim_normal = client.get(f"/api/v1/uavs/{registered_uav}/dashboard").json()
    assert dash_sim_normal["health"]["overall"] > 70.0

    # 3. Inject OVERHEATING fault
    fault_res = client.post(
        f"/api/v1/uavs/{registered_uav}/simulation/fault",
        json={"fault_type": "OVERHEATING"},
    )
    assert fault_res.status_code == 200

    # 4. Step simulation several times under fault conditions
    for _ in range(5):
        client.post(
            f"/api/v1/uavs/{registered_uav}/simulation/step",
            json={"dt": 0.5, "auto_ingest": True},
        )

    # 5. Check degraded dashboard
    dash_fault = client.get(f"/api/v1/uavs/{registered_uav}/dashboard").json()

    # Temperatures must be significantly elevated
    assert dash_fault["engine"]["cht"] > 190.0 or dash_fault["engine"]["egt"] > 700.0

    # Thermal or overall health must have dropped compared to normal baseline
    assert dash_fault["health"]["thermal"] < 100.0

    # Active fault or anomaly should be reflected
    analytics = dash_fault["analytics"]
    assert analytics["anomaly"]["score"] > 0.0 or len(analytics["faults"]) > 0

    # 6. Test Lubrication Failure: FaultInjector drops oil_pressure by 22 psi and raises vibration by 2.2
    client.post(
        f"/api/v1/uavs/{registered_uav}/simulation/fault",
        json={"fault_type": "LUBRICATION_FAILURE"},
    )
    for _ in range(5):
        client.post(
            f"/api/v1/uavs/{registered_uav}/simulation/step",
            json={"dt": 0.5, "auto_ingest": True},
        )

    dash_lube = client.get(f"/api/v1/uavs/{registered_uav}/dashboard").json()
    # Vibration increase from lubrication failure degrades mechanical health
    assert dash_lube["health"]["mechanical"] < 100.0
    # Overall health is reduced
    assert dash_lube["health"]["overall"] < 100.0

    # Test severe low oil pressure directly via telemetry
    severe_lube_telem = dict(sample_telemetry_dict)
    severe_lube_telem["oil_pressure"] = 10.0  # Well below 20 psi threshold
    client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=severe_lube_telem)

    dash_severe_lube = client.get(f"/api/v1/uavs/{registered_uav}/dashboard").json()
    assert dash_severe_lube["health"]["lubrication"] < 100.0

