from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
from typing import Any

from fastapi import WebSocket

from sih.dt.core.state import EngineState
from sih.dt.core.twin import DigitalTwin
from sih.dt.models.piston import PistonEngineModel
from sih.dt.simulation.engine import SyntheticEngineSimulator
from sih.dt.simulation.faults import FaultInjector


@dataclass
class UAVRecord:
    """Isolated state container for a single UAV digital twin."""
    uav_id: str
    engine_id: str = "ENG-DEFAULT"
    model_type: str = "piston"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    # Isolated Digital Twin & Simulation components
    twin: DigitalTwin = field(default_factory=lambda: DigitalTwin(PistonEngineModel()))
    simulator: SyntheticEngineSimulator = field(default_factory=SyntheticEngineSimulator)
    fault_injector: FaultInjector = field(default_factory=FaultInjector)

    # Latest operational state
    latest_state: EngineState = field(default_factory=EngineState)
    latest_analytics: dict[str, Any] = field(default_factory=dict)
    last_telemetry_time: datetime | None = None
    telemetry_count: int = 0

    # Sliding windows & history
    states_buffer: deque[EngineState] = field(default_factory=lambda: deque(maxlen=60))
    residual_history: list[list[float]] = field(default_factory=list)
    history: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=1000))

    # Real-time WebSocket clients
    ws_connections: set[WebSocket] = field(default_factory=set)
    lock: threading.Lock = field(default_factory=threading.Lock)


class TwinStateManager:
    """Thread-safe multi-UAV digital twin registry and state manager."""

    def __init__(self) -> None:
        self._uavs: dict[str, UAVRecord] = {}
        self._lock = threading.Lock()

    def register_uav(
        self,
        uav_id: str,
        engine_id: str = "ENG-DEFAULT",
        model_type: str = "piston",
        configuration: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UAVRecord:
        with self._lock:
            if uav_id in self._uavs:
                raise ValueError(f"UAV '{uav_id}' is already registered.")

            model = PistonEngineModel(**(configuration or {}))
            record = UAVRecord(
                uav_id=uav_id,
                engine_id=engine_id,
                model_type=model_type,
                twin=DigitalTwin(model),
                simulator=SyntheticEngineSimulator(),
                fault_injector=FaultInjector(),
                metadata=metadata or {},
            )
            self._uavs[uav_id] = record
            return record

    def get_uav(self, uav_id: str) -> UAVRecord | None:
        with self._lock:
            return self._uavs.get(uav_id)

    def get_or_create(self, uav_id: str) -> UAVRecord:
        """Convenience method to retrieve or auto-register a default UAV."""
        with self._lock:
            if uav_id not in self._uavs:
                record = UAVRecord(
                    uav_id=uav_id,
                    engine_id=f"ENG-{uav_id}",
                    model_type="piston",
                    twin=DigitalTwin(PistonEngineModel()),
                    simulator=SyntheticEngineSimulator(),
                    fault_injector=FaultInjector(),
                )
                self._uavs[uav_id] = record
            return self._uavs[uav_id]

    def exists(self, uav_id: str) -> bool:
        with self._lock:
            return uav_id in self._uavs

    def list_uavs(self) -> list[UAVRecord]:
        with self._lock:
            return list(self._uavs.values())

    def delete_uav(self, uav_id: str) -> bool:
        with self._lock:
            if uav_id in self._uavs:
                del self._uavs[uav_id]
                return True
            return False

    def count(self) -> int:
        with self._lock:
            return len(self._uavs)

    def clear(self) -> None:
        """Reset all registered twins (used in test fixtures)."""
        with self._lock:
            self._uavs.clear()


# Global singleton instance
_GLOBAL_STATE_MANAGER: TwinStateManager | None = None


def get_state_manager() -> TwinStateManager:
    global _GLOBAL_STATE_MANAGER
    if _GLOBAL_STATE_MANAGER is None:
        _GLOBAL_STATE_MANAGER = TwinStateManager()
    return _GLOBAL_STATE_MANAGER
