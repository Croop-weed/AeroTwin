from __future__ import annotations


def test_register_uav_success(client):
    payload = {
        "uav_id": "UAV-ALPHA",
        "engine_id": "ENG-101",
        "model_type": "piston",
        "metadata": {"operator": "base_station_1"},
    }
    res = client.post("/api/v1/uavs", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["uav_id"] == "UAV-ALPHA"
    assert data["engine_id"] == "ENG-101"
    assert data["metadata"]["operator"] == "base_station_1"


def test_register_duplicate_uav_conflict(client):
    payload = {"uav_id": "UAV-DUP"}
    res1 = client.post("/api/v1/uavs", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/uavs", json=payload)
    assert res2.status_code == 409


def test_list_and_get_uav(client):
    client.post("/api/v1/uavs", json={"uav_id": "UAV-1"})
    client.post("/api/v1/uavs", json={"uav_id": "UAV-2"})

    res = client.get("/api/v1/uavs")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    uav_ids = {u["uav_id"] for u in data["uavs"]}
    assert uav_ids == {"UAV-1", "UAV-2"}

    # Get single
    res_single = client.get("/api/v1/uavs/UAV-1")
    assert res_single.status_code == 200
    assert res_single.json()["uav_id"] == "UAV-1"

    # Nonexistent
    res_none = client.get("/api/v1/uavs/UAV-NONEXISTENT")
    assert res_none.status_code == 404


def test_delete_uav(client):
    client.post("/api/v1/uavs", json={"uav_id": "UAV-DEL"})
    res_del = client.delete("/api/v1/uavs/UAV-DEL")
    assert res_del.status_code == 200

    # Verify deleted
    res_get = client.get("/api/v1/uavs/UAV-DEL")
    assert res_get.status_code == 404
