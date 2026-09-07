# ML Layer Orchestration

This directory contains the orchestration scripts that implement the SIH digital twin's split ML architecture: **AI/ML Layer** and **Fault Detection & Predictive Analytics**.

## Architecture & Validation

As specified in the problem statement, the system is strictly split into two paradigms.

### 1. AI/ML Layer (Anomaly Detection & RUL) - `01_ai_ml_layer.py`
This layer focuses entirely on scoring the residual (expected vs. actual simulator output).
- **Anomaly Detection**: Trained on **our simulator's NORMAL data**. Scores how far telemetry deviates from healthy bounds.
- **RUL Estimation**: Scaffolded for Quantile Regression bands (P10/P50/P90).
- **Validation Dataset**: **NASA C-MAPSS**. 
- **Validation Status**: **Loader implemented, validation not yet run**. The loader in `data_loaders.py` is implemented, but RUL tuning on C-MAPSS is pending.

### 2. Fault Detection & Predictive Analytics - `02_fault_detection.py`
This layer consumes anomalous `ResidualWindow` objects and classifies the specific fault signature.

It is split by feature type:
- **Vibration-Based Faults** (Misfire, Combustion Instability, Abnormal Vibration):
  - **Limitation (IMPORTANT):** Our current simulator only emits a 1Hz scalar proxy for vibration, rather than a raw high-frequency kHz waveform. True CWRU-equivalent FFT analysis is therefore impossible on this synthetic data. We currently use simplified rolling statistical features (variance, short-window trend) as a proxy.
  - **Validation Dataset**: **CWRU Bearing Dataset**.
  - **Validation Status**: **Loader implemented, validation executed**.
- **Tabular/Multi-Mode Faults** (Injector Abnormalities, Lubrication Issues, Overheating):
  - **Validation Dataset**: **AI4I 2020 Predictive Maintenance Dataset**.
  - **Validation Status**: **Loader implemented, validation executed**.
- **Sensor Drift**:
  - Validated entirely synthetically via our simulator (sustained directional drift detection).

## Data Contracts
The two scripts communicate via the `ResidualWindow` object defined in `sih.dt.analytics.contracts`. The fault classifier is designed to only operate on windows that the anomaly layer has explicitly flagged as degraded.
