# AeroTwin Digital Twin API Reference

This document provides the complete API specification and frontend integration guide for the **AeroTwin / SIH Digital Twin** backend.

---

## 1. Overview & Architecture

The API layer is built on FastAPI and wraps the existing AeroTwin Digital Twin, simulation, and predictive analytics engine. It is designed to be **UAV-agnostic**, supporting multiple distinct aircraft digital twins concurrently while maintaining strict state isolation.

```text
       ┌────────────────────────┐
       │ External UAV / ECU /   │
       │   Simulator Client     │
       └───────────┬────────────┘
                   │ HTTP POST Telemetry / Simulation
                   ▼
       ┌────────────────────────┐
       │   FastAPI API Layer    │
       │     (/api/v1/...)      │
       └───────────┬────────────┘
                   │
                   ▼
       ┌────────────────────────┐
       │      TwinService       │
       └─────┬────────────┬─────┘
             │            │
             ▼            ▼
     ┌──────────────┐  ┌────────────────────────┐
     │ Digital Twin │  │   AnalyticsService     │
     │   (State)    │  │ (Anomaly, Faults, RUL, │
     └───────┬──────┘  │  Degradation, Sensors) │
             │         └──────────┬─────────────┘
             └────────────┬───────┘
                          ▼
       ┌────────────────────────────────────────┐
       │       TwinStateManager (In-Memory)     │
       └──────────┬──────────────────┬──────────┘
                  │                  │
                  ▼                  ▼
       ┌────────────────────┐ ┌─────────────────┐
       │ REST Dashboard API │ │ Real-Time WS    │
       │  (/dashboard)      │ │   (/ws)         │
       └──────────┬─────────┘ └────────┬────────┘
                  │                    │
                  ▼                    ▼
             [ Section B Frontend Dashboard ]
```

---

## 2. Getting Started

### Starting the Server
Run the API using `uv`:

```bash
uv run uvicorn sih.dt.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Interactive Documentation
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 3. Endpoints Reference

### 3.1 System Health

#### `GET /health`
Returns backend API process status and AI model readiness.

**Sample Response:**
```json
{
  "status": "ok",
  "service": "AeroTwin Digital Twin API",
  "version": "0.1.0",
  "models_ready": true,
  "active_uavs": 2,
  "timestamp": "2026-09-12T02:00:00Z"
}
```

---

### 3.2 UAV Registration & Multi-UAV Isolation

The backend supports multiple UAVs concurrently. Each UAV receives its own isolated Digital Twin, simulation engine, and time-series history ring buffer.

#### `POST /api/v1/uavs`
Register a new UAV digital twin.

**Request Payload:**
```json
{
  "uav_id": "UAV-ROTAX-01",
  "engine_id": "ENG-912-IS",
  "model_type": "piston",
  "configuration": {},
  "metadata": {
    "mission": "Alpha-Recon",
    "base": "Station-North"
  }
}
```

#### `GET /api/v1/uavs`
List all registered UAV digital twins.

#### `GET /api/v1/uavs/{uav_id}`
Retrieve registration details for a specific UAV.

#### `DELETE /api/v1/uavs/{uav_id}`
Unregister and remove all state associated with a UAV.

---

### 3.3 Telemetry Ingestion Contract

#### `POST /api/v1/uavs/{uav_id}/telemetry`
Ingest a real or simulated telemetry sample. Validates against the strict Digital Twin telemetry schema, advances the twin by $\Delta t$, computes subsystem health scores, runs anomaly detection and fault diagnosis, and broadcasts the updated state to WebSocket listeners.

**Request Payload:**
```json
{
  "timestamp": "2026-09-12T02:00:00Z",
  "rpm": 2450.0,
  "throttle": 55.0,
  "manifold_absolute_pressure": 72.5,
  "egt": 710.0,
  "cht": 182.0,
  "intake_air_temperature": 25.0,
  "ambient_temperature": 22.0,
  "oil_pressure": 38.5,
  "oil_temperature": 91.0,
  "fuel_flow": 17.8,
  "injection_timing_deg": 0.0,
  "vibration": 1.25,
  "ambient_pressure": 101.3,
  "battery_voltage": 13.8
}
```

**Response (HTTP 200):**
```json
{
  "uav_id": "UAV-ROTAX-01",
  "status": "processed",
  "timestamp": "2026-09-12T02:00:00Z",
  "overall_health": 98.4,
  "is_anomaly": false,
  "anomaly_score": 0.12,
  "active_fault": null
}
```

---

### 3.4 Section B Dashboard Snapshot (Hero Endpoint)

#### `GET /api/v1/uavs/{uav_id}/dashboard`
This is the primary endpoint for **Section B (Visualization & Output Presentation)**. It consolidates all parameters required for a complete live dashboard view into one structured response.

**Response Schema:**
```json
{
  "uav": {
    "uav_id": "UAV-ROTAX-01",
    "engine_id": "ENG-912-IS",
    "status": "active",
    "model_type": "piston"
  },
  "timestamp": "2026-09-12T02:00:00Z",
  "engine": {
    "rpm": 2450.0,
    "throttle": 55.0,
    "manifold_absolute_pressure": 72.5,
    "egt": 710.0,
    "cht": 182.0,
    "intake_air_temperature": 25.0,
    "ambient_temperature": 22.0,
    "oil_pressure": 38.5,
    "oil_temperature": 91.0,
    "fuel_flow": 17.8,
    "injection_timing_deg": 0.0,
    "vibration": 1.25,
    "ambient_pressure": 101.3,
    "battery_voltage": 13.8
  },
  "performance": {
    "estimated_torque": 122.4,
    "estimated_power": 31.4,
    "engine_load": 55.0,
    "fuel_efficiency": 1.76,
    "operating_time_seconds": 320.5
  },
  "temporal": {
    "previous_rpm": 2400.0,
    "rpm_rate": 100.0,
    "egt_rate": 5.0,
    "cht_rate": 1.5,
    "oil_temperature_rate": 0.2,
    "vibration_rate": 0.05
  },
  "health": {
    "overall": 98.4,
    "combustion": 100.0,
    "thermal": 96.2,
    "lubrication": 100.0,
    "mechanical": 97.5,
    "electrical": 100.0
  },
  "analytics": {
    "anomaly": {
      "is_anomaly": false,
      "score": 0.12,
      "confidence": 1.0,
      "timestamp": "2026-09-12T02:00:00Z"
    },
    "faults": [],
    "degradation": {
      "degradation_index": 0.016,
      "confidence": 1.0,
      "trend": "STABLE",
      "timestamp": "2026-09-12T02:00:00Z"
    },
    "rul": {
      "status": "AVAILABLE",
      "remaining_useful_life": 142.5,
      "lower_bound": 121.1,
      "upper_bound": 163.9,
      "confidence": 0.85,
      "timestamp": "2026-09-12T02:00:00Z"
    },
    "sensors": [
      {
        "sensor_name": "rpm",
        "status": "NORMAL",
        "confidence": 1.0,
        "anomaly_score": 0.0,
        "timestamp": "2026-09-12T02:00:00Z"
      },
      {
        "sensor_name": "egt",
        "status": "NORMAL",
        "confidence": 1.0,
        "anomaly_score": 0.0,
        "timestamp": "2026-09-12T02:00:00Z"
      }
    ]
  },
  "operating_conditions": {
    "rpm_ratio": 0.42,
    "throttle_ratio": 0.55,
    "map_ratio": 0.70,
    "fuel_flow_ratio": 0.36
  }
}
```

---

### 3.5 Real-Time WebSocket Streaming

#### `WS /api/v1/uavs/{uav_id}/ws`
Establishes a persistent bi-directional WebSocket connection.

- Upon connecting, the server immediately emits the current `DashboardSnapshotResponse` JSON frame.
- Whenever new telemetry is ingested or the simulation steps forward, an updated `DashboardSnapshotResponse` frame is broadcasted in real time.
- Clients can send `"ping"` to receive `{"type": "pong"}` heartbeats.

**JavaScript / Frontend WebSocket Example:**
```javascript
const socket = new WebSocket("ws://localhost:8000/api/v1/uavs/UAV-ROTAX-01/ws");

socket.onopen = () => {
  console.log("Connected to AeroTwin real-time telemetry stream");
};

socket.onmessage = (event) => {
  const snapshot = JSON.parse(event.data);
  // Update dashboard gauges and health monitors:
  updateHealthGauge(snapshot.health.overall);
  updateSubsystemBars(snapshot.health);
  updateEngineParameters(snapshot.engine);
  updateAnalyticsAlerts(snapshot.analytics);
};

socket.onerror = (err) => console.error("WebSocket error:", err);
```

---

### 3.6 Analytics & AI Endpoints

- `GET /api/v1/uavs/{uav_id}/analytics`: Complete analytics summary bundle.
- `GET /api/v1/uavs/{uav_id}/analytics/anomaly`: Current anomaly detection flag and score.
- `POST /api/v1/uavs/{uav_id}/analytics/anomaly`: Evaluate ad-hoc telemetry sample for anomalies without mutating state.
- `GET /api/v1/uavs/{uav_id}/faults`: Active diagnosed faults, confidence, severity, and evidence.
- `GET /api/v1/uavs/{uav_id}/analytics/rul`: Dual-Encoder LSTM Remaining Useful Life prediction.
- `GET /api/v1/uavs/{uav_id}/analytics/degradation`: Normalized degradation index ($0.0 \rightarrow 1.0$) and trend.
- `GET /api/v1/uavs/{uav_id}/analytics/sensors`: Status of individual sensors (`NORMAL`, `DRIFT`, `STUCK`, `UNKNOWN`).

---

### 3.7 Simulation Engine Endpoints

- `POST /api/v1/uavs/{uav_id}/simulation/start`: Initialize a synthetic engine session.
- `POST /api/v1/uavs/{uav_id}/simulation/step`: Step simulation by `dt` seconds (with optional `auto_ingest`).
- `POST /api/v1/uavs/{uav_id}/simulation/throttle`: Update throttle (0-100%).
- `POST /api/v1/uavs/{uav_id}/simulation/fault`: Inject or clear synthetic faults:
  - Supported faults: `OVERHEATING`, `LUBRICATION_FAILURE`, `INJECTOR_DEGRADATION`, `MISFIRE`, `COMBUSTION_INSTABILITY`, `ABNORMAL_VIBRATION`, `SENSOR_DRIFT`, `SENSOR_FAILURE`. Pass `null` or `"NONE"` to clear.
- `POST /api/v1/uavs/{uav_id}/simulation/reset`: Reset simulation and Digital Twin state.
- `GET /api/v1/uavs/{uav_id}/simulation/state`: Current simulation parameters and active fault.

---

### 3.8 Time Series & History

#### `GET /api/v1/uavs/{uav_id}/history?limit=100&start_time=...&end_time=...`
Returns timestamped historical records with engine measurements, health scores, and analytics for charting trends.
