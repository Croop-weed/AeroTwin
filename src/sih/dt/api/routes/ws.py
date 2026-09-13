from __future__ import annotations

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from sih.dt.api.dependencies import get_broadcast_service, get_state_manager, get_twin_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/uavs", tags=["Real-Time WebSockets"])


@router.websocket("/{uav_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    uav_id: str,
):
    """Real-time WebSocket endpoint streaming dashboard updates to frontend clients."""
    await websocket.accept()

    broadcast_service = get_broadcast_service()
    twin_service = get_twin_service()
    state_manager = get_state_manager()

    state_manager.get_or_create(uav_id)
    await broadcast_service.register(uav_id, websocket)

    try:
        # Immediately push current dashboard snapshot upon connection
        try:
            snapshot = twin_service.get_dashboard_snapshot(uav_id)
            await websocket.send_text(json.dumps(snapshot.model_dump(mode="json"), default=str))
        except Exception as exc:
            logger.debug(f"Error sending initial snapshot to ws: {exc}")

        # Keep connection open and handle any incoming client messages (e.g., ping)
        while True:
            data = await websocket.receive_text()
            if data.strip().lower() == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        await broadcast_service.unregister(uav_id, websocket)
    except Exception as exc:
        logger.debug(f"WebSocket client error: {exc}")
        await broadcast_service.unregister(uav_id, websocket)
