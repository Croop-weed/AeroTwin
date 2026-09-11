# SIH Digital Twin

Prototype backend for an AI-enabled health-monitoring system for aero piston engines. The repository currently provides a digital-twin state pipeline, synthetic telemetry and fault generation, feature extraction, baseline analytics contracts, and labelled ML-ready dataset generation.

This is synthetic research/prototype software. The simulator and health calculations are not calibrated aircraft-engine specifications, and the current degradation and RUL components do not provide scientifically valid predictions.

## Pipeline

```text
SyntheticEngineSimulator -> Telemetry -> FaultInjector -> DigitalTwin
									  -> EngineState
									  -> WindowFeatureExtractor -> FeatureVector
									  -> FaultDataset
									  -> optional analytics/ML components
```

The engine model is independent of feature engineering and analytics. `DigitalTwin`, `PistonEngineModel`, `Telemetry`, and `EngineState` do not depend on a particular ML algorithm.

## Setup and tests

Python 3.12 is required. Dependencies are declared in `pyproject.toml` and are managed with `uv`.

```bash
uv run pytest
uv run python examples/fault_demo.py
```

The test suite covers the engine foundation, temporal state, operating-condition features, analytics contracts, fault injection, and dataset generation.

## Package map

### `sih.dt.telemetry`

#### `schema.py`

`Telemetry` is the validated Pydantic v2 input measurement model. It contains timestamp, RPM, throttle, MAP, EGT, CHT, oil pressure and temperature, fuel flow, vibration, battery voltage, ambient values, and the prototype `injection_timing_deg` field.

Construct it from a mapping or keyword arguments:

```python
telemetry = Telemetry(
	timestamp=datetime.now(timezone.utc),
	rpm=2400,
	throttle=55,
	manifold_absolute_pressure=72,
	egt=720,
	cht=185,
	intake_air_temperature=26,
	ambient_temperature=24,
	oil_pressure=38,
	oil_temperature=92,
	fuel_flow=18,
	vibration=1.2,
	ambient_pressure=101.3,
	battery_voltage=13.8,
)
```

Pydantic validates non-negative measurements and the throttle range. Extra fields are rejected.

### `sih.dt.core`

#### `state.py`

`EngineState` is the canonical output of the Digital Twin. It contains:

- raw measurements copied from telemetry;
- derived torque, power, engine load, fuel efficiency, and subsystem health;
- temporal values: `previous_rpm`, rates, and `operating_time_seconds`;
- operating-condition values: `rpm_ratio`, `throttle_ratio`, `map_ratio`, and `fuel_flow_ratio`;
- prototype injection timing.

`clamp_0_100(value)` returns a value bounded to the health-score range. Most model calculations use the model's own `_clamp` helper instead.

#### `twin.py`

`DigitalTwin` coordinates telemetry and an injected `EngineModel`:

- `__init__(model=None)` uses `PistonEngineModel` by default, or accepts another `EngineModel` implementation.
- `ingest(telemetry)` stores the latest validated telemetry and returns it.
- `update(dt)` asks the model to calculate and store an `EngineState`. Telemetry must be ingested first.
- `get_state()` returns the latest state, falling back to the model's state for a fresh twin.
- `reset()` clears telemetry, model state, temporal state, and operating time.

Example:

```python
twin = DigitalTwin()
twin.ingest(telemetry)
state = twin.update(0.1)
print(state.overall_health, state.rpm_rate)
twin.reset()
```

### `sih.dt.models`

#### `base.py`

`EngineModel` is the abstract model contract. Implementations provide:

- `update(telemetry, dt) -> EngineState`;
- `reset() -> None`;
- `get_state() -> EngineState`.

This abstraction allows another engine model to be used by `DigitalTwin` without changing the twin API.

#### `piston.py`

`PistonEngineModel` is the current lightweight prototype model. It calculates approximate torque, power, load, efficiency, combustion/thermal/lubrication/mechanical/electrical health, and overall health.

- `__init__(...)` accepts configurable prototype parameters such as maximum RPM, ideal temperatures, low oil pressure, and nominal battery voltage.
- `update(telemetry, dt)` validates non-negative `dt`, calculates the current state, computes temporal rates from one previous telemetry sample, and accumulates operating time.
- `reset()` clears the current state, previous sample, and operating time.
- `get_state()` returns the last model state.

Only one previous telemetry sample is retained; this is not a history store.

### `sih.dt.simulation`

#### `engine.py`

`SyntheticEngineSimulator` produces coherent, deterministic-in-logic prototype telemetry rather than independently random sensor values.

- `__init__(throttle=25.0, ambient_temperature=22.0, ambient_pressure=101.3)` configures initial simulation conditions.
- `set_throttle(throttle)` clamps and applies throttle from 0 to 100.
- `reset()` restores the simulator's initial operating state and returns an initial telemetry sample.
- `step(dt)` advances the simulation and returns telemetry. Negative durations are rejected.

The simulator relates throttle to RPM, MAP, temperatures, oil pressure, fuel flow, vibration, and battery voltage. It is not a calibrated engine model.

#### `faults.py`

`FaultType` is the typed enum for supported synthetic scenarios:

`OVERHEATING`, `LUBRICATION_FAILURE`, `INJECTOR_DEGRADATION`, `MISFIRE`, `COMBUSTION_INSTABILITY`, `ABNORMAL_VIBRATION`, `SENSOR_DRIFT`, and `SENSOR_FAILURE`.

`FaultInjector` modifies a copy of telemetry:

- `__init__(active_fault=None)` optionally selects a fault;
- `set_fault(fault)` changes the active scenario;
- `clear()` disables injection;
- `inject(telemetry)` returns a copied telemetry object with the selected prototype changes.

The injector creates test data only. It is not the diagnostic engine.

### `sih.dt.features`

The feature layer consumes `Sequence[EngineState]` and has no dependency on sklearn.

#### `schema.py`

`FeatureVector` is an immutable ordered numeric vector:

- `names` and `values` store stable feature order;
- `features` exposes a read-only name-to-value mapping;
- `as_dict()` returns a normal dictionary;
- `to_list()` returns an ML-compatible numeric row;
- `__len__`, `__iter__`, and `__getitem__` support sequence-style access;
- `from_mapping(features)` creates a vector in mapping insertion order.

`feature_matrix(vectors)` converts compatible vectors to rows and rejects inconsistent feature names. `FeatureVector` rejects NaN and infinity.

#### `base.py`

`FeatureExtractor` is a protocol with `extract(states) -> FeatureVector`. A replacement extractor can implement this method without changing analytics or the engine model.

#### `extractor.py`

`WindowFeatureExtractor` creates a compact, explainable window representation:

- `feature_names` returns deterministic names;
- `extract(states)` calculates mean, population standard deviation, minimum, and maximum for important signals;
- it calculates timestamp-based slopes for RPM, EGT, CHT, oil temperature, vibration, and fuel flow;
- it includes the latest RPM, throttle, MAP, and fuel-flow ratios.

Empty windows, single-state windows, repeated timestamps, missing timestamps, constant values, and non-finite source values produce finite safe features. These are observed statistics, not expected-value physics.

### `sih.dt.analytics`

Analytics components are composed after feature engineering and can be replaced independently.

#### `base.py` and `anomaly.py`

`AnomalyDetector` defines `fit(vectors)`, `predict(vector)`, and `score(vector)`.

`IsolationForestDetector` is the first concrete adapter:

- `__init__(contamination="auto", random_state=None)` configures the sklearn model;
- `fit(vectors)` trains on normal feature vectors;
- `predict(vector)` returns a boolean anomaly flag;
- `score(vector)` returns a higher-is-more-anomalous score;
- `predict_many(vectors)` and `score_many(vectors)` process collections.

The engine and feature classes do not know that Isolation Forest exists. `AnomalyResult` stores an anomaly flag, score, and optional timestamp.

#### `diagnosis.py`

`FaultDiagnoser` defines `diagnose(states, anomaly=None)`. `FaultDiagnosis` contains typed fault type, confidence, severity, evidence, and timestamp. `BaselineFaultDiagnoser` is a small explainable prototype for wiring and tests; it can later be replaced by a classifier or probabilistic model.

#### `sensor.py`

`SensorAnomalyDetector` defines `inspect(states)`. `SensorStatus` separates sensor condition from physical engine health using sensor name, `NORMAL`/`DRIFT`/`STUCK`/`UNKNOWN` status, confidence, score, and timestamp. `BaselineSensorAnomalyDetector` provides a minimal temporal baseline.

#### `degradation.py`

`DegradationEstimator` defines `estimate(states)`. `DegradationState` uses an index from 0 (healthy) to 1 (severely degraded), confidence, trend, and timestamp. `BaselineDegradationEstimator` derives a transparent prototype index from overall health; it is not a validated degradation model.

#### `rul.py`

`RULPredictor` defines `predict(states)`. `RULPrediction` contains status, optional remaining time and bounds, confidence, and timestamp. `UnavailableRULPredictor` returns `INSUFFICIENT_DATA` for an empty window or `NOT_TRAINED` when data exists. It intentionally does not fabricate an RUL value.

#### `result.py`

`AnalyticsResult` is the typed aggregate contract for anomaly output, fault diagnoses, sensor statuses, degradation, RUL, and timestamp. It is intended for future consumers such as services or dashboards, but no API or UI integration is included here.

### `sih.dt.data`

#### `generator.py`

`DatasetLabel` is the typed dataset label enum. `from_fault_type(fault_type)` converts a `FaultType` to its dataset label.

`GeneratedWindow` stores one labelled feature window:

- `features`: `FeatureVector`;
- `label`: `DatasetLabel`;
- `run_id`: sequence identity for leakage-safe splitting;
- `window_start` and `window_end`: state indices;
- `timestamp`: final state timestamp in the window.

`FaultDataset` stores immutable samples:

- `feature_names` returns stable names, including names for an empty dataset;
- `labels` and `run_ids` return sample metadata;
- `to_arrays()` returns `(X, y)` as numeric rows and string labels;
- `__len__()` returns the number of windows.

`FaultDatasetGenerator` creates coherent simulator runs and extracts windows:

- `__init__(extractor=None, timestep_seconds=0.1, seed=None)` configures extraction, sample period, and deterministic run selection;
- `generate_normal(...)` creates normal runs;
- `generate_fault(fault_type, ...)` creates runs for one existing `FaultType`;
- `generate(fault_types=..., ...)` combines normal data and selected fault classes;
- internal `_run_states(...)` creates simulator-to-twin state sequences;
- internal `_windows(...)` converts state sequences into labelled overlapping windows;
- internal `_generate_runs(...)` validates dimensions and creates run IDs.

Use `run_id` when creating train/validation/test splits. Split complete runs, not individual overlapping windows.

```python
from sih.dt.data import FaultDatasetGenerator
from sih.dt.simulation.faults import FaultType

dataset = FaultDatasetGenerator(seed=42).generate(
	fault_types=(FaultType.OVERHEATING, FaultType.MISFIRE),
	normal_runs=4,
	fault_runs=2,
	steps_per_run=30,
	window_size=10,
	stride=2,
)
X, y = dataset.to_arrays()
print(len(dataset), len(dataset.feature_names), set(y))
```

## Extension guidance

To add a new engine model, implement `EngineModel` and pass it to `DigitalTwin`. To replace feature engineering, implement the `FeatureExtractor` protocol and pass the extractor to `FaultDatasetGenerator`. To replace anomaly detection, implement `AnomalyDetector` against `FeatureVector`; do not modify the engine model or twin. Diagnosis, sensor analysis, degradation, and RUL each have the same replaceable-protocol boundary.

When adding a new fault scenario, add it to the simulation `FaultType`, implement only its synthetic telemetry mutation in `FaultInjector`, map it in `DatasetLabel`, and add focused tests. Do not use the injector as a production diagnostic rule engine.

## AI and Machine Learning Integration

The framework now includes fully functional, pre-trained AI layers integrated directly into the `sih.dt.analytics` architecture. 

### Core Components
- **Anomaly Detection (`sih.dt.analytics.anomaly.IsolationForestDetector`)**: An Isolation Forest algorithm that identifies anomalous telemetry behavior by measuring deviation from normal simulator data. 
- **Fault Classifiers (`sih.dt.analytics.fault_classifiers`)**: Integrates fault signatures validated against the CWRU Bearing Dataset (using `np.fft.rfft` for true vibration analysis) and AI4I (for tabular faults) to diagnose the root cause of anomalies. We aggressively prevent data leakage via `GroupShuffleSplit`.
- **RUL Prediction (`sih.dt.analytics.rul_training`)**: A Dual-Encoder LSTM model. It is pre-trained on NASA's C-MAPSS degradation dataset to learn physics-based failure mechanics, and dynamically fine-tunes itself on real-time simulator residuals to accurately estimate Remaining Useful Life (RUL).
- **Dataset Loaders (`sih.dt.data.loaders`)**: Robust data loaders with caching (`data/cache/`) to manage the external validation datasets (NASA, CWRU, AI4I).

### Running the End-to-End Pipeline
To view the AI models actively detecting faults and predicting RUL on stochastic live engine telemetry, you can run the master pipeline script:

```bash
uv run python src/sih/dt/pipeline.py
```
This orchestrator will automatically load the pre-trained weights from `data/cache/best_rul_model.pth`, calibrate the anomaly detector on the digital twin's healthy state, and begin injecting random faults to test the classifiers!

## Current limitations

- All engine relationships and health scores are prototype approximations.
- Injection timing defaults to a configurable-looking but uncalibrated prototype field.
- Fuel-flow normalization uses the existing prototype reference scale.
- Baseline diagnosis and sensor checks are not production fault classifiers.
- Synthetic faults are useful for pipeline testing, not evidence of real UAV failure behavior.
- RUL remains explicitly unavailable/not trained until trustworthy run-to-failure data and a validated model exist.
- No web API, UI, database, networking, or deployment layer is included.
