# ML Layer Orchestration

This directory contains the orchestration scripts that implement the SIH digital twin's split ML architecture: **AI/ML Layer** and **Fault Detection & Predictive Analytics**.

## End-to-End Execution - `03_full_pipeline.py`
The `03_full_pipeline.py` script serves as the master orchestrator. It brings together the fully stochastic digital twin (which generates real-world, noisy UAV telemetry), the anomaly detector, the RUL predictor, and the fault classifiers into a single, cohesive loop. It outputs real-time cycle data alongside critical anomaly triggers and diagnoses.

## Architecture & Validation

As specified in the problem statement, the system is strictly split into two paradigms.

### 1. AI/ML Layer (Anomaly Detection & RUL) - `01_ai_ml_layer.py`
This layer focuses entirely on scoring the residual (expected vs. actual simulator output).
- **Anomaly Detection**: Trained on **our simulator's NORMAL data**. Scores how far telemetry deviates from healthy bounds using an Isolation Forest.
- **RUL Estimation**: Uses a **Dual-Encoder LSTM**. It is pretrained on NASA C-MAPSS to learn degradation physics, and fine-tunes a separate simulator-encoder on the fly to adapt to our proprietary residual channels.
- **Validation Dataset**: **NASA C-MAPSS**. 
- **Validation Status**: **Completed & Fully Functional**. The data is cached locally to speed up execution, baseline subtraction is applied to align domains, and the LSTM successfully pretrains and infers. We strictly utilize `GroupShuffleSplit` by Engine ID to ensure zero data leakage across engine runs during validation.

### 2. Fault Detection & Predictive Analytics - `02_fault_detection.py`
This layer consumes anomalous `ResidualWindow` objects and classifies the specific fault signature.

It is split by feature type:
- **Vibration-Based Faults** (Misfire, Combustion Instability, Abnormal Vibration):
  - **Feature Extraction**: We utilize `np.fft.rfft` to extract true frequency-domain features (Peak FFT frequency and total Spectral Energy) alongside time-domain statistics (RMS, Crest Factor) to characterize vibration signatures.
  - **Validation Dataset**: **CWRU Bearing Dataset**.
  - **Validation Status**: **Completed**. We implemented file-level `GroupShuffleSplit` to rigorously prevent label leakage (ensuring training and testing windows never come from the same physical drive-end bearing file).
- **Tabular/Multi-Mode Faults** (Injector Abnormalities, Lubrication Issues, Overheating):
  - **Validation Dataset**: **AI4I 2020 Predictive Maintenance Dataset**.
  - **Validation Status**: **Loader implemented, validation executed**.
- **Sensor Drift**:
  - Validated entirely synthetically via our simulator (sustained directional drift detection).

## Data Caching
All three external validation datasets (C-MAPSS, CWRU, AI4I) are aggressively preprocessed (smoothed, windowed, baseline-subtracted, and FFT transformed). To ensure the orchestration scripts run instantly, `data_loaders.py` caches the finalized DataFrames to `data/cache/*.pkl` upon first execution.

## Data Contracts
The two scripts communicate via the `ResidualWindow` object defined in `sih.dt.analytics.contracts`. The fault classifier is designed to only operate on windows that the anomaly layer has explicitly flagged as degraded.
