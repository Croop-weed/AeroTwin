from __future__ import annotations

import json
import logging
from typing import Any
from fastapi import WebSocket

from sih.dt.api.state.manager import TwinStateManager, get_state_manager

logger = logging.getLogger(__name__)


class BroadcastService:
    """Manages real-time WebSocket connections and broadcasts per UAV."""

    def __init__(self, state_manager: TwinStateManager | None = None) -> None:
        self.state_manager = state_manager or get_state_manager()

    async def register(self, uav_id: str, websocket: WebSocket) -> None:
        uav = self.state_manager.get_or_create(uav_id)
        with uav.lock:
            uav.ws_connections.add(websocket)
        logger.info(f"WebSocket client connected for UAV '{uav_id}'. Total clients: {len(uav.ws_connections)}")

    async def unregister(self, uav_id: str, websocket: WebSocket) -> None:
        uav = self.state_manager.get_uav(uav_id)
        if uav is not None:
            with uav.lock:
                uav.ws_connections.discard(websocket)
            logger.info(f"WebSocket client disconnected for UAV '{uav_id}'. Remaining: {len(uav.ws_connections)}")

    async def broadcast_json(self, uav_id: str, data: dict[str, Any]) -> None:
        uav = self.state_manager.get_uav(uav_id)
        if uav is None or not uav.ws_connections:
            return

        payload = json.dumps(data, default=str)
        dead_connections: list[WebSocket] = []

        with uav.lock:
            active_connections = list(uav.ws_connections)

        for ws in active_connections:
            try:
                await ws.send_text(payload)
            except Exception as exc:
                logger.debug(f"Failed to send to WebSocket client: {exc}")
                dead_connections.append(ws)

        if dead_connections:
            with uav.lock:
                for ws in dead_connections:
                    uav.ws_connections.discard(ws)


_GLOBAL_BROADCAST_SERVICE: BroadcastService | None = None


def get_broadcast_service() -> BroadcastService:
    global _GLOBAL_BROADCAST_SERVICE
    if _GLOBAL_BROADCAST_SERVICE is None:
        _GLOBAL_BROADCAST_SERVICE = BroadcastService()
    return _GLOBAL_BROADCAST_SERVICE
