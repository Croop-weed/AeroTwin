from __future__ import annotations

from sih.dt.core.twin import DigitalTwin
from sih.dt.models.piston import PistonEngineModel
from sih.dt.simulation.engine import SyntheticEngineSimulator
from sih.dt.simulation.faults import FaultInjector, FaultType


def run_case(label: str, fault: FaultType | None, simulator: SyntheticEngineSimulator, twin: DigitalTwin) -> None:
    injector = FaultInjector(fault)
    print(f"\nCASE: {label}")

    for step in range(5):
        telemetry = simulator.step(0.1)
        injected = injector.inject(telemetry)
        twin.ingest(injected)
        state = twin.update(0.1)
        print(
            f"{step + 1:02d} | rpm={state.rpm:7.1f} | egt={state.egt:7.1f} | "
            f"cht={state.cht:7.1f} | oil={state.oil_pressure:6.1f} | vib={state.vibration:5.2f} | "
            f"health={state.overall_health:5.1f}"
        )


simulator = SyntheticEngineSimulator(throttle=25.0)
twin = DigitalTwin(PistonEngineModel())

run_case("NORMAL", None, simulator, twin)
run_case("OVERHEATING", FaultType.OVERHEATING, simulator, twin)
run_case("LUBRICATION_FAILURE", FaultType.LUBRICATION_FAILURE, simulator, twin)
run_case("INJECTOR_DEGRADATION", FaultType.INJECTOR_DEGRADATION, simulator, twin)
