from __future__ import annotations

from datetime import datetime, timedelta, timezone


def test_history_recording_and_limiting(client, registered_uav, sample_telemetry_dict):
    base_time = datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc)

    # Ingest 5 telemetry samples
    for i in range(5):
        telem = dict(sample_telemetry_dict)
        telem["timestamp"] = (base_time + timedelta(seconds=i)).isoformat()
        telem["rpm"] = 2000.0 + i * 100.0
        client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=telem)

    # Fetch all
    res = client.get(f"/api/v1/uavs/{registered_uav}/history")
    assert res.status_code == 200
    data = res.json()
    assert data["uav_id"] == registered_uav
    assert data["total_points"] == 5

    # Verify chronological ordering
    rpms = [p["measurements"]["rpm"] for p in data["points"]]
    assert rpms == [2000.0, 2100.0, 2200.0, 2300.0, 2400.0]

    # Test limit=2
    res_lim = client.get(f"/api/v1/uavs/{registered_uav}/history?limit=2")
    assert res_lim.status_code == 200
    lim_data = res_lim.json()
    assert lim_data["total_points"] == 2
    assert [p["measurements"]["rpm"] for p in lim_data["points"]] == [2300.0, 2400.0]
