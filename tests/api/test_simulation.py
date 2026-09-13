from __future__ import annotations


def test_simulation_workflow(client, registered_uav):
    # 1. Start simulation
    res_start = client.post(
        f"/api/v1/uavs/{registered_uav}/simulation/start",
        json={"throttle": 30.0, "ambient_temperature": 20.0, "ambient_pressure": 101.3},
    )
    assert res_start.status_code == 200
    assert res_start.json()["is_active"] is True
    assert res_start.json()["throttle"] == 30.0
    assert res_start.json()["latest_telemetry"]["throttle"] == 30.0

    # 2. Step simulation
    res_step = client.post(
        f"/api/v1/uavs/{registered_uav}/simulation/step",
        json={"dt": 0.2, "auto_ingest": True},
    )
    assert res_step.status_code == 200
    step_data = res_step.json()
    assert step_data["step_dt"] == 0.2
    assert "telemetry" in step_data
    assert "dashboard_snapshot" in step_data

    # 3. Throttle change
    res_thr = client.post(
        f"/api/v1/uavs/{registered_uav}/simulation/throttle",
        json={"throttle": 75.0},
    )
    assert res_thr.status_code == 200
    assert res_thr.json()["throttle"] == 75.0

    # 4. Inject fault
    res_fault = client.post(
        f"/api/v1/uavs/{registered_uav}/simulation/fault",
        json={"fault_type": "OVERHEATING"},
    )
    assert res_fault.status_code == 200
    assert res_fault.json()["active_fault"] == "OVERHEATING"

    # Step with fault
    res_step_fault = client.post(
        f"/api/v1/uavs/{registered_uav}/simulation/step",
        json={"dt": 0.5, "auto_ingest": True},
    )
    assert res_step_fault.status_code == 200
    # Overheating should raise CHT and EGT
    cht = res_step_fault.json()["telemetry"]["cht"]
    assert cht > 160.0

    # 5. Clear fault
    res_clear = client.post(
        f"/api/v1/uavs/{registered_uav}/simulation/fault",
        json={"fault_type": None},
    )
    assert res_clear.status_code == 200
    assert res_clear.json()["active_fault"] is None

    # 6. Reset simulation
    res_reset = client.post(f"/api/v1/uavs/{registered_uav}/simulation/reset")
    assert res_reset.status_code == 200
    assert res_reset.json()["simulated_time_seconds"] == 0.0


def test_start_simulation_clears_previous_dashboard_session(client, registered_uav):
    client.post(
        f"/api/v1/uavs/{registered_uav}/simulation/start",
        json={"throttle": 45.0},
    )
    client.post(
        f"/api/v1/uavs/{registered_uav}/simulation/step",
        json={"dt": 0.5, "auto_ingest": True},
    )

    restarted = client.post(
        f"/api/v1/uavs/{registered_uav}/simulation/start",
        json={"throttle": 20.0},
    )
    history = client.get(f"/api/v1/uavs/{registered_uav}/history")

    assert restarted.status_code == 200
    assert restarted.json()["latest_telemetry"]["throttle"] == 20.0
    assert history.status_code == 200
    assert history.json()["total_points"] == 0


def test_invalid_fault_type_rejected(client, registered_uav):
    res = client.post(
        f"/api/v1/uavs/{registered_uav}/simulation/fault",
        json={"fault_type": "NON_EXISTENT_FAULT_XYZ"},
    )
    assert res.status_code == 400
