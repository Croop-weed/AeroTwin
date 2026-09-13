"""AeroTwin Live Dashboard Simulation Producer Script.

Connects to the running FastAPI server (http://localhost:8000 by default),
drives the synthetic engine simulator, streams validated telemetry into
the Digital Twin, and automatically broadcasts live updates via WebSockets
to any open AeroTwin Ground Control Dashboard in real time.

Scenario Stages:
  Stage 1: Normal Cruise Operation (Healthy telemetry, 95%+ health)
  Stage 2: Fault Injection (OVERHEATING: EGT/CHT climb, thermal degradation, active fault alert)
  Stage 3: Fault Cleared / Engine Recovery (Temperatures cool, health recovers)

Usage:
  # Terminal 1:
  uv run uvicorn sih.dt.api.main:app --reload --host 0.0.0.0 --port 8000

  # Terminal 2:
  uv run python examples/dashboard_demo.py
  # or continuous mode:
  uv run python examples/dashboard_demo.py --continuous --uav UAV-001
"""

from __future__ import annotations

import argparse
import sys
import time
import httpx


def print_banner(msg: str) -> None:
    line = "=" * 76
    print(f"\n{line}\n   {msg}\n{line}")


def post(client: httpx.Client, path: str, **kwargs: object) -> httpx.Response:
    response = client.post(path, **kwargs)
    response.raise_for_status()
    return response


def run_demo(
    base_url: str = "http://localhost:8000",
    uav_id: str = "UAV-001",
    step_delay: float = 0.4,
    continuous: bool = False,
) -> None:
    print_banner(f"AeroTwin Live Dashboard Simulator Producer -> {base_url}")
    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Health check
    try:
        res = client.get("/health")
        if res.status_code != 200:
            print(f"[ERROR] Backend /health returned {res.status_code}: {res.text}")
            sys.exit(1)
        print(f"[OK] Connected to AeroTwin Backend: {res.json()['status']}")
    except httpx.ConnectError:
        print(
            "\n[ERROR] Could not connect to FastAPI server at http://localhost:8000!\n"
            "Please ensure the backend is running in another terminal:\n"
            "  uv run uvicorn sih.dt.api.main:app --reload --host 0.0.0.0 --port 8000\n"
        )
        sys.exit(1)

    # 2. Register UAV if not already registered
    try:
        registration = client.post(
            "/api/v1/uavs",
            json={
                "uav_id": uav_id,
                "engine_id": f"ROTAX-914-TURBO-{uav_id}",
                "model_type": "piston",
                "metadata": {
                    "mission": f"PATROL-FLIGHT-{uav_id}",
                    "operator": "Airborne Systems GCS",
                    "location": "Sector-4 Operational Zone",
                },
            },
        )
        if registration.status_code not in (201, 409):
            registration.raise_for_status()
        print(f"[OK] Registered UAV '{uav_id}'")
    except httpx.HTTPError as exc:
        print(f"[ERROR] Could not register or find UAV '{uav_id}': {exc}")
        return

    iteration = 1
    while True:
        if continuous and iteration > 1:
            print_banner(f"RESTARTING FLIGHT DEMO (Iteration {iteration})")

        # 3. Start/Reset Simulation
        post(
            client,
            f"/api/v1/uavs/{uav_id}/simulation/start",
            json={
                "throttle": 45.0,
                "ambient_temperature": 24.0,
                "ambient_pressure": 101.3,
            },
        )
        print(f"[OK] Initialized engine simulation session for {uav_id} (Throttle: 45.0%)")

        # -------------------------------------------------------------
        # STAGE 1: Normal Cruise Operation
        # -------------------------------------------------------------
        print_banner("STAGE 1: NORMAL FLIGHT OPERATION (System Nominal)")
        print(f"{'STEP':>5} | {'RPM':>7} | {'EGT (C)':>7} | {'CHT (C)':>7} | {'HEALTH':>7} | {'ANOMALY':>7} | {'FAULT':<14}")
        print("-" * 76)

        for step in range(1, 16):
            res = post(
                client,
                f"/api/v1/uavs/{uav_id}/simulation/step",
                json={"dt": 0.5, "auto_ingest": True},
            )
            data = res.json()
            snap = data.get("dashboard_snapshot")
            if snap:
                eng = snap["engine"]
                hlt = snap["health"]
                anom = snap["analytics"]["anomaly"]["is_anomaly"]
                fault = snap["analytics"]["faults"][0]["fault_type"] if snap["analytics"]["faults"] else "NONE"
                print(
                    f"{step:5d} | {eng['rpm']:7.1f} | {eng['egt']:7.1f} | {eng['cht']:7.1f} | "
                    f"{hlt['overall']:6.1f}% | {str(anom):>7} | {fault:<14}"
                )
            time.sleep(step_delay)

        # -------------------------------------------------------------
        # STAGE 2: Fault Injection (OVERHEATING)
        # -------------------------------------------------------------
        print_banner("STAGE 2: INJECTING FAULT -> OVERHEATING")
        post(
            client,
            f"/api/v1/uavs/{uav_id}/simulation/fault",
            json={"fault_type": "OVERHEATING"},
        )
        print(">> Injected synthetic thermal failure. Observe live rising EGT/CHT on dashboard!")
        print(f"{'STEP':>5} | {'RPM':>7} | {'EGT (C)':>7} | {'CHT (C)':>7} | {'HEALTH':>7} | {'ANOMALY':>7} | {'FAULT':<14}")
        print("-" * 76)

        for step in range(16, 36):
            res = post(
                client,
                f"/api/v1/uavs/{uav_id}/simulation/step",
                json={"dt": 0.5, "auto_ingest": True},
            )
            data = res.json()
            snap = data.get("dashboard_snapshot")
            if snap:
                eng = snap["engine"]
                hlt = snap["health"]
                anom = snap["analytics"]["anomaly"]["is_anomaly"]
                fault = snap["analytics"]["faults"][0]["fault_type"] if snap["analytics"]["faults"] else "NONE"
                print(
                    f"{step:5d} | {eng['rpm']:7.1f} | {eng['egt']:7.1f} | {eng['cht']:7.1f} | "
                    f"{hlt['overall']:6.1f}% | {str(anom):>7} | {fault:<14}"
                )
            time.sleep(step_delay)

        # -------------------------------------------------------------
        # STAGE 3: Clear Fault & Recover
        # -------------------------------------------------------------
        print_banner("STAGE 3: CLEARING FAULT -> SYSTEM RECOVERY")
        post(
            client,
            f"/api/v1/uavs/{uav_id}/simulation/fault",
            json={"fault_type": None},
        )
        print(">> Fault cleared via API. Watch engine telemetry and health recover in real time!")
        print(f"{'STEP':>5} | {'RPM':>7} | {'EGT (C)':>7} | {'CHT (C)':>7} | {'HEALTH':>7} | {'ANOMALY':>7} | {'FAULT':<14}")
        print("-" * 76)

        for step in range(36, 52):
            res = post(
                client,
                f"/api/v1/uavs/{uav_id}/simulation/step",
                json={"dt": 0.5, "auto_ingest": True},
            )
            data = res.json()
            snap = data.get("dashboard_snapshot")
            if snap:
                eng = snap["engine"]
                hlt = snap["health"]
                anom = snap["analytics"]["anomaly"]["is_anomaly"]
                fault = snap["analytics"]["faults"][0]["fault_type"] if snap["analytics"]["faults"] else "NONE"
                print(
                    f"{step:5d} | {eng['rpm']:7.1f} | {eng['egt']:7.1f} | {eng['cht']:7.1f} | "
                    f"{hlt['overall']:6.1f}% | {str(anom):>7} | {fault:<14}"
                )
            time.sleep(step_delay)

        # Mission Summary check
        res_rep = client.get(f"/api/v1/uavs/{uav_id}/mission-report")
        if res_rep.status_code == 200:
            rep = res_rep.json()
            print_banner("MISSION REPORT SUMMARY")
            print(f"Mission: {rep['mission_id']} | UAV: {rep['uav_id']} | Engine: {rep['engine_id']}")
            print(f"Duration: {rep['duration_seconds']:.1f}s | Points: {rep['total_telemetry_points']}")
            print(f"Health: Avg={rep['average_health']:.1f}% | Min={rep['min_health']:.1f}% | Max={rep['max_health']:.1f}%")
            print(f"Anomalies: {rep['anomalies_detected']} | Fault Events: {rep['fault_events_count']}")
            print(f"Maintenance Advisory: {rep['maintenance_advisory']}")

        if not continuous:
            print_banner("Demo Run Complete! Dashboard updated successfully without refresh.")
            break

        iteration += 1
        time.sleep(2.0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AeroTwin Live Dashboard Demo Script")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of AeroTwin API")
    parser.add_argument("--uav", default="UAV-001", help="UAV ID to simulate")
    parser.add_argument("--delay", type=float, default=0.35, help="Delay between steps in seconds")
    parser.add_argument("--continuous", action="store_true", help="Run continuously in a loop")
    args = parser.parse_args()

    run_demo(
        base_url=args.url,
        uav_id=args.uav,
        step_delay=args.delay,
        continuous=args.continuous,
    )
