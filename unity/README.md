# AeroTwin Unity UAV Simulator

This is the Unity client for the SIH AeroTwin Digital Twin. It lives inside the existing repository and does not contain a second backend or a copy of the Python engine/ML pipeline.

## Unity version

The project now targets **Unity 6000.6.0f1 (Unity 6.6)** after import with the installed editor.

## Setup

1. Open the repository's `unity/` folder from Unity Hub.
2. Open `Assets/Scenes/Simulator.unity` for the flight demonstrator or `Assets/Scenes/DigitalTwin.unity` for the twin-focused view.
3. Select `AeroTwinSimulator` or `AeroTwinDigitalTwin` in the scene and set `connectionMode` to `Offline`, `Mock`, or `Live`.
4. For Live mode, start the existing API from the repository root:

   ```bash
   uv run uvicorn sih.dt.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Press Play. The default connection is `http://127.0.0.1:8000`, UAV ID `UAV-001`, engine ID `ENG-UAV-001`, and telemetry rate 10 Hz.

## Controls

`W/S` changes throttle, `A/D` changes heading, Arrow Up/Down changes pitch, `Q/E` changes roll, `Y/H` adjusts target RPM, `T/G` adjusts injection timing, and `R` resets the aircraft. The HUD provides pause, reset, start, and supported fault injection controls.

## Modes

- **Offline**: flight controls and visualization run without backend traffic.
- **Mock**: local dashboard-shaped responses exercise the HUD and Digital Twin view without a server.
- **Live**: registers the UAV, posts strict engine telemetry, and receives dashboard snapshots over WebSocket.

## API contract

Unity posts `TelemetryIngestRequest` to `POST /api/v1/uavs/{uav_id}/telemetry` using the backend's exact snake_case fields. It registers with `POST /api/v1/uavs`, injects faults through `POST /api/v1/uavs/{uav_id}/simulation/fault`, and uses the existing simulation start/reset endpoints. Dashboard state arrives from `ws://127.0.0.1:8000/api/v1/uavs/{uav_id}/ws`.

The current backend DashboardSnapshot contract contains engine, health, analytics, and operating data but no aircraft pose. Unity therefore interpolates the Digital Twin visual from the pilot flight state while engine health, faults, analytics, and RUL remain backend-authoritative. Adding backend pose fields later only requires extending the dashboard DTO and twin controller.

## Ownership

Unity owns the lightweight aircraft movement, controls, camera, visualization, and telemetry generation. FastAPI owns registration and orchestration. Python owns engine behavior, health, faults, anomaly detection, degradation, and RUL. The existing React frontend is unchanged.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the module map and replacement path for a future JSBSim dynamics implementation.