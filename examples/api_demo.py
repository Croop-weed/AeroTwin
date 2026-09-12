"""Stream generated telemetry through the real AeroTwin API.

The simulator and fault injector generate raw telemetry locally. Every sample
is then validated and processed by the FastAPI telemetry endpoint, so the
backend Digital Twin, pipeline analytics, history, and WebSocket dashboard all
observe the same data.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

import httpx

from sih.dt.simulation.engine import SyntheticEngineSimulator
from sih.dt.simulation.faults import FaultInjector, FaultType


def post_telemetry(
    client: httpx.Client,
    uav_id: str,
    simulator: SyntheticEngineSimulator,
    injector: FaultInjector,
    dt: float,
) -> dict[str, Any]:
    telemetry = injector.inject(simulator.step(dt))
    response = client.post(
        f"/api/v1/uavs/{uav_id}/telemetry",
        json=telemetry.model_dump(mode="json"),
    )
    response.raise_for_status()
    return response.json()


def run_demo(
    base_url: str = "http://localhost:8000",
    uav_id: str = "UAV-001",
    step_delay: float = 0.35,
    continuous: bool = False,
) -> None:
    client = httpx.Client(base_url=base_url, timeout=10.0)
    simulator = SyntheticEngineSimulator(
        throttle=45.0,
        ambient_temperature=24.0,
        ambient_pressure=101.3,
    )
    injector = FaultInjector()

    try:
        health = client.get("/health")
        health.raise_for_status()
        print(f"[OK] Connected to AeroTwin Backend: {health.json()['status']}")

        registration = client.post(
            "/api/v1/uavs",
            json={
                "uav_id": uav_id,
                "engine_id": f"ROTAX-914-TURBO-{uav_id}",
                "model_type": "piston",
                "metadata": {"mission": f"PATROL-FLIGHT-{uav_id}"},
            },
        )
        if registration.status_code not in (201, 409):
            registration.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"[ERROR] Could not connect to or register with the API: {exc}")
        sys.exit(1)

    iteration = 1
    try:
        while True:
            simulator.reset()
            injector.clear()
            print(f"\n=== Flight telemetry demo {iteration} ({uav_id}) ===")

            stages = (
                ("NORMAL", None, 15),
                ("OVERHEATING", FaultType.OVERHEATING, 20),
                ("RECOVERY", None, 16),
            )
            for stage_name, fault, count in stages:
                injector.set_fault(fault)
                print(f"\n-- {stage_name} --")
                for step in range(count):
                    result = post_telemetry(client, uav_id, simulator, injector, 0.5)
                    print(
                        f"step={step + 1:02d} health={result['overall_health']:6.1f}% "
                        f"anomaly={str(result['is_anomaly']):5s} "
                        f"fault={result['active_fault'] or 'NONE'}"
                    )
                    time.sleep(step_delay)

            if not continuous:
                break
            iteration += 1
    except KeyboardInterrupt:
        print("\nDemo stopped.")
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AeroTwin live dashboard demo")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of AeroTwin API")
    parser.add_argument("--uav", default="UAV-001", help="UAV ID shown by the dashboard")
    parser.add_argument("--delay", type=float, default=0.35, help="Delay between streamed steps in seconds")
    parser.add_argument("--continuous", action="store_true", help="Repeat the scenario continuously")
    args = parser.parse_args()
    run_demo(args.url, args.uav, args.delay, args.continuous)
