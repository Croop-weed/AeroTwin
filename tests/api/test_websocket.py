from __future__ import annotations

import json


def test_websocket_streaming(client, registered_uav, sample_telemetry_dict):
    with client.websocket_connect(f"/api/v1/uavs/{registered_uav}/ws") as websocket:
        # 1. Receive initial snapshot on connect
        initial_msg = websocket.receive_text()
        initial_data = json.loads(initial_msg)
        assert "uav" in initial_data
        assert initial_data["uav"]["uav_id"] == registered_uav

        # 2. Test ping-pong
        websocket.send_text("ping")
        pong_msg = websocket.receive_text()
        assert json.loads(pong_msg).get("type") == "pong"

        # 3. Ingest telemetry via HTTP API
        updated_telem = dict(sample_telemetry_dict)
        updated_telem["rpm"] = 3250.0
        res = client.post(f"/api/v1/uavs/{registered_uav}/telemetry", json=updated_telem)
        assert res.status_code == 200

        # 4. Verify live update delivered over WebSocket
        live_frame = websocket.receive_text()
        live_data = json.loads(live_frame)
        assert live_data["engine"]["rpm"] == 3250.0
