"""AeroTwin API End-to-End Demonstration Script.

Demonstrates:
1. Checking API health.
2. Registering an isolated UAV Digital Twin (UAV-DEMO-99).
3. Starting synthetic flight simulation at 35% throttle.
4. Advancing normal flight and inspecting the healthy dashboard.
5. Dynamically injecting an OVERHEATING fault via the simulation API.
6. Observing live changes in engine telemetry, thermal health degradation, and fault alerts.
7. Clearing the fault and observing stabilization.
"""

from __future__ import annotations

import json
from fastapi.testclient import TestClient

from sih.dt.api.main import app


def print_banner(text: str) -> None:
    print("\n" + "=" * 70)
    print(f"   {text}")
    print("=" * 70)


def print_snapshot(title: str, snap: dict) -> None:
    print(f"\n--- {title} ---")
    uav = snap["uav"]
    engine = snap["engine"]
    health = snap["health"]
    analytics = snap["analytics"]
    perf = snap["performance"]

    print(f"UAV ID: {uav['uav_id']} | Engine: {uav['engine_id']} | Status: {uav['status']}")
    print(
        f"Engine Metrics: RPM={engine['rpm']:6.1f} | Throttle={engine['throttle']:4.1f}% | "
        f"EGT={engine['egt']:5.1f} C | CHT={engine['cht']:5.1f} C | "
        f"Oil Press={engine['oil_pressure']:4.1f} psi | Vib={engine['vibration']:4.2f} mm/s"
    )
    print(
        f"Health Scores:  Overall={health['overall']:5.1f}% | Thermal={health['thermal']:5.1f}% | "
        f"Combustion={health['combustion']:5.1f}% | Lubrication={health['lubrication']:5.1f}%"
    )
    print(
        f"Performance:    Torque={perf['estimated_torque']:5.1f} Nm | Power={perf['estimated_power']:5.1f} kW | "
        f"Load={perf['engine_load']:5.1f}% | OpTime={perf['operating_time_seconds']:5.1f} s"
    )

    anom = analytics["anomaly"]
    deg = analytics["degradation"]
    rul = analytics["rul"]
    faults = analytics["faults"]

    print(
        f"Analytics:      Anomaly={anom['is_anomaly']} (score: {anom['score']:.2f}) | "
        f"Degradation={deg['degradation_index']:.3f} ({deg['trend']}) | "
        f"RUL={rul['status']} (cycles: {rul.get('remaining_useful_life')})"
    )
    if faults:
        fault_strs = [f"{f['fault_type']} (conf: {f['confidence']:.2f})" for f in faults]
        print(f"Active Faults:  {', '.join(fault_strs)}")
    else:
        print("Active Faults:  NONE (System Nominal)")


def main():
    print_banner("AeroTwin Digital Twin - API End-to-End Demo")

    with TestClient(app) as client:
        # 1. API Server Health Check
        print("\n[Step 1] Checking API Server Health...")
        res_health = client.get("/health")
        print(f"  -> Response HTTP {res_health.status_code}: {res_health.json()}")

        # 2. Register UAV
        uav_id = "UAV-DEMO-99"
        print(f"\n[Step 2] Registering UAV '{uav_id}'...")
        res_reg = client.post(
            "/api/v1/uavs",
            json={
                "uav_id": uav_id,
                "engine_id": "ENG-ROTAX-912-IS",
                "model_type": "piston",
                "metadata": {"mission": "recon_flight_07", "payload": "eo_ir_gimbal"},
            },
        )
        print(f"  -> Response HTTP {res_reg.status_code}: {res_reg.json()['uav_id']} registered.")

        # 3. Start Simulation
        print(f"\n[Step 3] Initializing simulation for '{uav_id}' at 35% cruise throttle...")
        client.post(
            f"/api/v1/uavs/{uav_id}/simulation/start",
            json={"throttle": 35.0, "ambient_temperature": 22.0, "ambient_pressure": 101.3},
        )

        # 4. Step normal flight
        print(f"\n[Step 4] Stepping normal flight simulation (5 steps x 0.5s)...")
        for step in range(5):
            res_step = client.post(
                f"/api/v1/uavs/{uav_id}/simulation/step",
                json={"dt": 0.5, "auto_ingest": True},
            )

        # 5. Fetch Dashboard Snapshot under normal flight
        res_dash_normal = client.get(f"/api/v1/uavs/{uav_id}/dashboard")
        print_snapshot("NORMAL CRUISE FLIGHT SNAPSHOT", res_dash_normal.json())

        # 6. Inject OVERHEATING fault
        print_banner("INJECTING FAULT: OVERHEATING")
        print(f"\n[Step 5] Injecting OVERHEATING scenario via API...")
        res_fault = client.post(
            f"/api/v1/uavs/{uav_id}/simulation/fault",
            json={"fault_type": "OVERHEATING"},
        )
        print(f"  -> Fault state updated: {res_fault.json()['active_fault']}")

        # 7. Advance flight with fault active
        print(f"\n[Step 6] Advancing flight simulation with OVERHEATING active (6 steps x 0.5s)...")
        for step in range(6):
            client.post(
                f"/api/v1/uavs/{uav_id}/simulation/step",
                json={"dt": 0.5, "auto_ingest": True},
            )

        # 8. Fetch Dashboard Snapshot under fault conditions
        res_dash_fault = client.get(f"/api/v1/uavs/{uav_id}/dashboard")
        print_snapshot("OVERHEATING FAULT FLIGHT SNAPSHOT", res_dash_fault.json())

        # 9. Clear fault and recover
        print_banner("CLEARING FAULT & RESTORING NOMINAL OPERATION")
        print(f"\n[Step 7] Clearing fault via API...")
        client.post(
            f"/api/v1/uavs/{uav_id}/simulation/fault",
            json={"fault_type": None},
        )
        for step in range(5):
            client.post(
                f"/api/v1/uavs/{uav_id}/simulation/step",
                json={"dt": 0.5, "auto_ingest": True},
            )

        res_dash_recovered = client.get(f"/api/v1/uavs/{uav_id}/dashboard")
        print_snapshot("RECOVERED FLIGHT SNAPSHOT", res_dash_recovered.json())

        # 10. Check Historical Points
        print(f"\n[Step 8] Retrieving time-series history (limit=5)...")
        res_hist = client.get(f"/api/v1/uavs/{uav_id}/history?limit=5")
        hist = res_hist.json()
        print(f"  -> Total recorded history points: {hist['total_points']}")

        print_banner("AeroTwin API Demo Finished Successfully!")


if __name__ == "__main__":
    main()
