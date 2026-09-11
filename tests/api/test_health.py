from __future__ import annotations


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "AeroTwin" in data["service"]
    assert "/docs" in data["docs_url"]


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "AeroTwin Digital Twin API"
    assert "models_ready" in data
    assert "active_uavs" in data
    assert isinstance(data["active_uavs"], int)
