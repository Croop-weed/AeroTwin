# AeroTwin Analytics & Remaining Useful Life (RUL) Module (`src/sih/dt/analytics`)

The `src/sih/dt/analytics` module provides the core intelligence, anomaly detection, fault diagnosis, degradation tracking, sensor health monitoring, and **Remaining Useful Life (RUL)** estimation for the AeroTwin Digital Twin engine system.

---

## 🛠️ Module Architecture Overview

The analytics subsystem is designed with a **decoupled, multi-tier architecture**:
1. **Abstract Protocols & Contracts (`base.py`, `contracts.py`)**: Defines clean interfaces (`AnomalyDetector`, `RULPredictor`, `FaultDiagnoser`) and inter-layer contract data structures (`ResidualWindow`) ensuring ML algorithms remain loosely coupled from business domain code.
2. **Rule-Based & Physics Baselines (`degradation.py`, `diagnosis.py`, `sensor.py`, `rul.py`)**: Provide transparent fallbacks when ML models are uncalibrated or when telemetry data buffers are insufficient.
3. **Deep Learning & Machine Learning Models (`rul_model.py`, `anomaly.py`, `fault_classifiers.py`, `rul_training.py`)**:
   - **Dual-Encoder LSTM (`AeroTwinRULModel`)**: RUL estimation network utilizing transfer learning between NASA C-MAPSS benchmark physics and real-time simulator residuals.
   - **Isolation Forest (`IsolationForestDetector`)**: Unsupervised anomaly detection on multidimensional residual feature vectors.
   - **Random Forest Classifiers (`VibrationFaultClassifier`, `TabularFaultClassifier`)**: Supervised fault classification for vibration instabilities, injector degradation, overheating, and lubrication issues.

---

## 📂 File Directory & Component Reference

| File | Primary Responsibilities | Key Classes & Functions |
| :--- | :--- | :--- |
| [base.py](file:///home/harshit/Desktop/SIH/src/sih/dt/analytics/base.py) | Protocol definitions for anomaly detectors | `AnomalyDetector` |
| [contracts.py](file:///home/harshit/Desktop/SIH/src/sih/dt/analytics/contracts.py) | Inter-layer data transfer contracts | `ResidualWindow` |
| [result.py](file:///home/harshit/Desktop/SIH/src/sih/dt/analytics/result.py) | Combined analytics summary container | `AnalyticsResult` |
| [anomaly.py](file:///home/harshit/Desktop/SIH/src/sih/dt/analytics/anomaly.py) | Unsupervised anomaly detection | `IsolationForestDetector`, `AnomalyResult` |
| [degradation.py](file:///home/harshit/Desktop/SIH/src/sih/dt/analytics/degradation.py) | Physical degradation tracking | `BaselineDegradationEstimator`, `DegradationState`, `DegradationTrend` |
| [diagnosis.py](file:///home/harshit/Desktop/SIH/src/sih/dt/analytics/diagnosis.py) | Baseline fault diagnosis rules | `BaselineFaultDiagnoser`, `FaultDiagnosis`, `FaultType` |
| [fault_classifiers.py](file:///home/harshit/Desktop/SIH/src/sih/dt/analytics/fault_classifiers.py) | Supervised ML fault classification | `VibrationFaultClassifier`, `TabularFaultClassifier`, `detect_sensor_drift()`, `validate_against_cwru()`, `validate_against_ai4i()` |
| [sensor.py](file:///home/harshit/Desktop/SIH/src/sih/dt/analytics/sensor.py) | Temporal sensor anomaly & drift check | `BaselineSensorAnomalyDetector`, `SensorStatus`, `SensorCondition` |
| [rul.py](file:///home/harshit/Desktop/SIH/src/sih/dt/analytics/rul.py) | RUL domain schemas & fallbacks | `RULPrediction`, `RULStatus`, `RULPredictor`, `UnavailableRULPredictor` |
| [rul_model.py](file:///home/harshit/Desktop/SIH/src/sih/dt/analytics/rul_model.py) | PyTorch Dual-Encoder LSTM neural network | `AeroTwinRULModel` |
| [rul_training.py](file:///home/harshit/Desktop/SIH/src/sih/dt/analytics/rul_training.py) | Pretraining, fine-tuning, and dataset loaders | `CMAPSSWindowDataset`, `validate_against_cmapss()`, `RULEstimator`, `main()` |

---

## 🔍 Detailed Class & Function Breakdown

### 1. `contracts.py` & `base.py`
- **`ResidualWindow`**: Dataclass holding residual metrics (`channel_residuals`), timestamp range (`start_time`, `end_time`), anomaly score (`anomaly_score`), and threshold flag (`is_anomalous`). Passed from anomaly detection into fault classification.
- **`AnomalyDetector`**: Python `Protocol` defining `.fit()`, `.predict()`, and `.score()`.

### 2. `result.py`
- **`AnalyticsResult`**: Pydantic `BaseModel` aggregating all sub-analyses into a single payload: `anomaly`, `fault_diagnoses`, `sensor_statuses`, `degradation`, `rul`, and `timestamp`.

### 3. `anomaly.py`
- **`IsolationForestDetector`**: Scikit-Learn `IsolationForest` wrapper fitting normal operational feature matrices and scoring candidate telemetry windows.

### 4. `diagnosis.py` & `fault_classifiers.py`
- **`FaultType`**: Enum containing target faults: `MISFIRE`, `INJECTOR_ABNORMALITY`, `LUBRICATION_ISSUE`, `SENSOR_DRIFT_OR_FAILURE`, `COMBUSTION_INSTABILITY`, `OVERHEATING`, `ABNORMAL_VIBRATION`.
- **`BaselineFaultDiagnoser`**: Heuristic diagnoser checking parameter rate-of-change ratios (EGT rate, CHT rate, oil pressure, vibration).
- **`VibrationFaultClassifier`**: Random Forest classifier evaluating vibration-based residual features (`mean`, `std`, `max_abs`, `slope`).
- **`TabularFaultClassifier`**: Random Forest classifier evaluating EGT, oil pressure, and fuel flow residual features.
- **`detect_sensor_drift()`**: Detects sustained unidirectional residual drift ($EGT_{res, mean} > 20.0$ and $|EGT_{res, slope}| > 0.5$).

### 5. `degradation.py`
- **`BaselineDegradationEstimator`**: Computes `degradation_index` ($0.0 \rightarrow 1.0$) based on engine health loss and calculates trend (`STABLE`, `IMPROVING`, `WORSENING`).

### 6. `sensor.py`
- **`BaselineSensorAnomalyDetector`**: Evaluates 8 key sensor streams (`rpm`, `egt`, `cht`, `oil_pressure`, `oil_temperature`, `fuel_flow`, `vibration`, `battery_voltage`) to flag `STUCK` (constant reading over window) or `DRIFT` conditions.

### 7. `rul.py`
- **`RULStatus`**: Enum representing estimation state (`UNAVAILABLE`, `INSUFFICIENT_DATA`, `NOT_TRAINED`, `AVAILABLE`).
- **`RULPrediction`**: Pydantic schema for RUL results.
- **`UnavailableRULPredictor`**: Fallback predictor used when history is insufficient (<30 cycles) or model is uncalibrated.

### 8. `rul_model.py` (`AeroTwinRULModel`)
PyTorch Dual-Encoder LSTM (`nn.Module`):
- **Door A Encoder (`cmapss_encoder`)**: MLP mapping 14 NASA C-MAPSS sensor channels $\rightarrow$ 32-dim latent space.
- **Door B Encoder (`sim_encoder`)**: MLP mapping 6 simulator residual channels $\rightarrow$ 32-dim latent space.
- **Shared LSTM Core (`lstm`)**: Single-layer LSTM (`hidden_size=64`, `batch_first=True`) encoding temporal physics.
- **RUL Predictor Head (`rul_predictor`)**: Linear layer mapping last LSTM hidden state $\rightarrow$ scalar RUL cycle estimate.
- **Core Freezing Methods**: `freeze_shared_core()` and `unfreeze_shared_core()` for domain adaptation.

### 9. `rul_training.py`
- **`validate_against_cmapss()`**: Pretrains `AeroTwinRULModel` on NASA C-MAPSS run-to-failure dataset (100 epochs, early stopping, MSE loss). Saves weights to `data/cache/best_rul_model.pth`.
- **`RULEstimator`**: Wraps model, freezes shared core, and exposes `fine_tune_and_predict(history, true_rul)` for online fine-tuning of `sim_encoder` on incoming residual windows.

---

## 🧮 Remaining Useful Life (RUL) Evaluation Parameters

Evaluating RUL requires data transfer across **three distinct layers**: Physical Telemetry $\rightarrow$ AI Model Input Tensor $\rightarrow$ API Output Payload.

```mermaid
flowchart LR
    subgraph Raw Telemetry
        T1[EngineState Telemetry]
        P1[Physics Reference Model]
    end

    subgraph Feature Residual Extraction
        R[6 Residual Channels]
    end

    subgraph AI Model (AeroTwinRULModel)
        W[Sliding Window: 30 Cycles]
        B[Door B Simulator Encoder: 6 -> 32]
        L[Shared LSTM Core: 32 -> 64]
        P[RUL Predictor Head: 64 -> 1]
    end

    subgraph API Endpoint Response
        API[RULResponse Payload]
    end

    T1 --> P1
    T1 & P1 --> R
    R --> W
    W -->|Tensor: 1x30x6| B
    B --> L --> P
    P -->|Cycles| API
```

### A. Raw Engine State Parameters (Physics Input)
The system calculates residual deviations by comparing live `EngineState` telemetry against the `PhysicsReferenceModel`:

| Telemetry Parameter | Symbol / Variable | Unit | Description |
| :--- | :--- | :--- | :--- |
| Engine RPM | `rpm` | RPM | Rotational speed of engine |
| Exhaust Gas Temperature | `egt` | °C | Temperature of exhaust gases |
| Cylinder Head Temp | `cht` | °C | Cylinder head temperature |
| Oil Pressure | `oil_pressure` | PSI | Lubrication system oil pressure |
| Oil Temperature | `oil_temperature` | °C | Lubrication system oil temperature |
| Fuel Flow Rate | `fuel_flow` | L/h | Volumetric fuel consumption rate |
| Vibration Level | `vibration` | g | Engine structural vibration magnitude |

---

### B. AI Model Input Parameters (`sim_dim = 6` Channels)
The RUL model (`AeroTwinRULModel.forward_sim`) consumes a **sequence of 6 residual mean values** calculated as $(Expected_{Physics} - Actual_{Observed})$:

$$\vec{r}_t = \begin{bmatrix} r_{\text{vibration}} \\ r_{\text{egt}} \\ r_{\text{cht}} \\ r_{\text{oil\_pressure}} \\ r_{\text{oil\_temperature}} \\ r_{\text{fuel\_flow}} \end{bmatrix}$$

| # | Residual Channel Name | Extracted Key (`schema.py`) | Meaning |
| :-: | :--- | :--- | :--- |
| **1** | Vibration Residual | `vibration_residual_mean` | Mechanical imbalance / bearing wear proxy |
| **2** | EGT Residual | `egt_residual_mean` | Combustion efficiency / thermal degradation |
| **3** | CHT Residual | `cht_residual_mean` | Cooling capacity degradation |
| **4** | Oil Pressure Residual | `oil_pressure_residual_mean` | Lubrication pump/line degradation |
| **5** | Oil Temp Residual | `oil_temperature_residual_mean` | Heat exchanger degradation |
| **6** | Fuel Flow Residual | `fuel_flow_residual_mean` | Fuel injector clogging/leakage |

---

### C. AI Model Hyperparameters & Tensor Dimensions

| Parameter | Configuration Value | Description |
| :--- | :--- | :--- |
| **Sequence Length (`seq_len`)** | `30` cycles | Minimum history required before RUL inference is activated |
| **Input Tensor Shape** | `(Batch=1, Seq_Len=30, Sim_Dim=6)` | Tensor passed into `forward_sim(x_tensor)` |
| **Encoder Latent Dim** | `32` | Non-linear MLP representation dimension |
| **LSTM Hidden Units** | `64` | Recurrent state memory dimension |
| **Output Head** | `1` scalar float | Estimated Remaining Useful Life in operational cycles |
| **Fine-Tuning Optimizer** | Adam (`lr=1e-3`) | Fine-tunes `sim_encoder` weights while LSTM is frozen |
| **Pretraining Dataset** | NASA C-MAPSS (FD001) | 14-sensor benchmark dataset used for Door A physics pretraining |

---

### D. API Integration & Response Parameters (`RULResponse`)

The API exposes RUL estimation via HTTP endpoints (`GET /api/v1/uavs/{uav_id}/analytics/rul` and `GET /api/v1/uavs/{uav_id}/analytics`).

#### API Service Ingestion Logic (`analytics_service.py`):
1. Verifies if `residual_history` contains $\ge 30$ historical residual vectors.
2. If sequence $< 30$, returns `status="INSUFFICIENT_DATA"` with `remaining_useful_life=None`.
3. If sequence $\ge 30$, converts historical residual vectors to PyTorch float32 tensor $(1, 30, 6)$ and calls `forward_sim()`.

#### API Response Payload Fields (`RULResponse`):

```json
{
  "status": "AVAILABLE",
  "remaining_useful_life": 124.5,
  "confidence": 0.85,
  "lower_bound": 105.8,
  "upper_bound": 143.2,
  "timestamp": "2026-09-12T18:50:00Z"
}
```

| Field Name | Type | Constraints / Calculation | Description |
| :--- | :--- | :--- | :--- |
| `status` | `RULStatus` | String (`AVAILABLE`, `INSUFFICIENT_DATA`, `NOT_TRAINED`, `UNAVAILABLE`) | Operational state of the RUL engine |
| `remaining_useful_life` | `float \| null` | $\ge 0.0$ cycles (e.g., `124.5`) | Model point-estimate of remaining cycles until threshold failure |
| `confidence` | `float` | $0.0 \le c \le 1.0$ (Default: `0.85` for ML model, `0.0` for fallbacks) | Statistical confidence metric |
| `lower_bound` | `float \| null` | $\max(0.0, \text{RUL} \times 0.85)$ | 15% conservative lower uncertainty boundary |
| `upper_bound` | `float \| null` | $\text{RUL} \times 1.15$ | 15% optimistic upper uncertainty boundary |
| `timestamp` | `datetime \| null` | ISO 8601 UTC timestamp | Time of evaluation |

---

## ⚡ Quick Execution Example

To run the standalone RUL training and validation pipeline:

```bash
python -m sih.dt.analytics.rul_training
```

Or execute the full analytics pipeline demo:

```bash
python -m sih.dt.pipeline
```
