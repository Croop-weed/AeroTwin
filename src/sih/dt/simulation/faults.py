from __future__ import annotations

from enum import Enum

from sih.dt.telemetry.schema import Telemetry


class FaultType(str, Enum):
    OVERHEATING = "OVERHEATING"
    LUBRICATION_FAILURE = "LUBRICATION_FAILURE"
    INJECTOR_DEGRADATION = "INJECTOR_DEGRADATION"


class FaultInjector:
    """Prototype fault injection for synthetic engine telemetry.

    This is intentionally deterministic and lightweight. It modifies a copied
    Telemetry instance without mutating the original object.
    """

    def __init__(self, active_fault: FaultType | None = None) -> None:
        self.active_fault: FaultType | None = active_fault

    def set_fault(self, fault: FaultType | None) -> None:
        self.active_fault = fault

    def clear(self) -> None:
        self.active_fault = None

    def inject(self, telemetry: Telemetry) -> Telemetry:
        payload = telemetry.model_dump()
        injected = Telemetry(**payload)

        if self.active_fault is None:
            return injected

        if self.active_fault is FaultType.OVERHEATING:
            injected.cht += 60.0
            injected.egt += 55.0
            injected.oil_temperature += 25.0

        elif self.active_fault is FaultType.LUBRICATION_FAILURE:
            injected.oil_pressure = max(0.0, injected.oil_pressure - 22.0)
            injected.oil_temperature += 18.0
            injected.vibration += 2.2

        elif self.active_fault is FaultType.INJECTOR_DEGRADATION:
            injected.fuel_flow += 6.0
            injected.egt += 35.0
            injected.rpm = max(0.0, injected.rpm * 0.9)

        return Telemetry(**injected.model_dump())
