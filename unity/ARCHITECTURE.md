# Unity Architecture

## Runtime flow

```text
Pilot input
  -> AircraftController
  -> IFlightDynamics / SimpleFlightDynamics
  -> FlightState
  -> AeroTwinClient
  -> ITelemetryTransport / HttpTelemetryTransport
  -> FastAPI -> Python Digital Twin and ML analytics
  -> RealtimeWebSocketTransport
  -> DashboardSnapshot
  -> DigitalTwinController and EngineeringHud
```

The Unity flight loop is independent from telemetry transmission. `AeroTwinClient` samples at its configured rate (10 Hz by default), so rendering FPS does not control network traffic. Only `PilotUAV` owns `IFlightDynamics`; `DigitalTwinUAV` has no flight controller or independent simulation and mirrors the pilot pose with a fixed visual offset. Its propeller uses backend dashboard RPM when available.

## Project structure

- `Assets/Scripts/Flight`: `IFlightDynamics` and the stable, low-fidelity `SimpleFlightDynamics` implementation, including smoothed deterministic engine telemetry.
- `Assets/Scripts/Aircraft`: pilot aircraft composition, keyboard engine controls, and propeller animation.
- `Assets/Scripts/Networking`: exact backend DTOs, HTTP registration/telemetry/fault commands, and WebSocket snapshot transport.
- `Assets/Scripts/DigitalTwin`: interpolation of the visual twin and storage of backend snapshots.
- `Assets/Scripts/UI`: engineering HUD and live health/analytics/fault display.
- `Assets/Scripts/Camera`: chase camera independent from aircraft control.
- `Assets/Scenes`: `Simulator.unity` and `DigitalTwin.unity`.
- `Assets/Models`, `Assets/Materials`, `Assets/Prefabs`, `Assets/Environment`, `Assets/UI`: replacement/extension locations.

## Backend ownership and endpoints

Unity uses:

- `POST /api/v1/uavs` for registration.
- `POST /api/v1/uavs/{uav_id}/telemetry` for strict engine telemetry.
- `POST /api/v1/uavs/{uav_id}/simulation/start` and `/simulation/reset` for explicit operator commands.
- `POST /api/v1/uavs/{uav_id}/simulation/fault` for supported fault injection.
- `WS /api/v1/uavs/{uav_id}/ws` for `DashboardSnapshot` updates.

Unity never calculates engine thermodynamics, subsystem health, fault diagnoses, degradation, or RUL. Mock mode is intentionally a local transport substitute for demonstrations without the API; it is not a second engine model.

In Live mode, normal operation posts PilotUAV telemetry. When a backend simulation fault is injected, Unity starts/steps the existing FastAPI simulation and temporarily stops posting competing manual samples; clearing or resetting the fault returns to PilotUAV telemetry publishing. This keeps backend fault effects from being overwritten by the client loop.

## Future JSBSim integration

Implement `JSBSimFlightDynamics : IFlightDynamics`, instantiate it in `AircraftController`, and preserve the `FlightState` output contract. Telemetry, networking, HUD, camera, Digital Twin, and visual model replacement will not need to change.

## Replacing the placeholder aircraft

Place an `.fbx`, `.glb`, `.obj`, or `.unitypackage` under `Assets/Models/`. Replace only the `VisualModel` children created by `AeroTwinBootstrap.CreateAircraft`; preserve the aircraft root, `AircraftController`, `PropellerController`, and camera target transform. Flight logic uses transforms and state, not mesh topology.

## Verification status

The project has been imported, compiled, and built with Unity 6000.6.0f1. The Linux player was run headlessly in Offline, Mock, and Live modes; Live mode connected to FastAPI, opened the WebSocket, and posted telemetry at the configured rate.