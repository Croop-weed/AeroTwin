from datetime import datetime, timedelta, timezone
import math

import pytest

from sih.dt.analytics import (
    AnalyticsResult,
    BaselineDegradationEstimator,
    BaselineFaultDiagnoser,
    BaselineSensorAnomalyDetector,
    DegradationTrend,
    IsolationForestDetector,
    RULStatus,
    SensorCondition,
    UnavailableRULPredictor,
)
from sih.dt.analytics.anomaly import AnomalyResult
from sih.dt.core.state import EngineState
from sih.dt.features import WindowFeatureExtractor
from sih.dt.features.schema import FeatureVector
from sih.dt.simulation.engine import SyntheticEngineSimulator
from sih.dt.simulation.faults import FaultInjector, FaultType
from sih.dt.core.twin import DigitalTwin
from sih.dt.models.piston import PistonEngineModel


BASE_TIME = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)


def states_for(values: list[float], field: str = "rpm") -> list[EngineState]:
    return [
        EngineState(timestamp=BASE_TIME + timedelta(seconds=index), **{field: value})
        for index, value in enumerate(values)
    ]


def test_feature_vector_is_deterministic_and_finite():
    extractor = WindowFeatureExtractor()
    states = states_for([1000.0, 1200.0, 1400.0])

    first = extractor.extract(states)
    second = extractor.extract(states)

    assert first == second
    assert first.names == extractor.feature_names
    assert len(first.names) == len(set(first.names))
    assert all(math.isfinite(value) for value in first.values)


def test_feature_statistics_and_positive_negative_slopes():
    extractor = WindowFeatureExtractor()
    states = [
        EngineState(timestamp=BASE_TIME + timedelta(seconds=index), rpm=value, egt=200 - value / 10)
        for index, value in enumerate([1000.0, 1200.0, 1400.0])
    ]

    vector = extractor.extract(states).features

    assert vector["rpm_mean"] == pytest.approx(1200.0)
    assert vector["rpm_std"] == pytest.approx((80000 / 3) ** 0.5)
    assert vector["rpm_min"] == 1000.0
    assert vector["rpm_max"] == 1400.0
    assert vector["rpm_slope"] == pytest.approx(200.0)
    assert vector["egt_slope"] == pytest.approx(-20.0)


def test_feature_extractor_handles_empty_single_constant_and_repeated_time_windows():
    extractor = WindowFeatureExtractor()

    for states in (
        [],
        [EngineState(timestamp=BASE_TIME, rpm=1200.0)],
        [EngineState(timestamp=BASE_TIME + timedelta(seconds=index), rpm=1200.0) for index in range(3)],
        [EngineState(timestamp=BASE_TIME, rpm=1000.0), EngineState(timestamp=BASE_TIME, rpm=1300.0)],
    ):
        vector = extractor.extract(states)
        assert all(math.isfinite(value) for value in vector.values)
        assert vector.features["rpm_slope"] == 0.0 if len(states) < 2 or states[0].timestamp == states[-1].timestamp else True


def test_non_finite_state_values_are_sanitized():
    vector = WindowFeatureExtractor().extract(
        [EngineState(timestamp=BASE_TIME, rpm=float("nan"), egt=float("inf"))]
    )

    assert all(math.isfinite(value) for value in vector.values)
    assert vector.features["rpm_mean"] == 0.0
    assert vector.features["egt_max"] == 0.0


def test_operating_condition_features_are_included_and_change():
    extractor = WindowFeatureExtractor()
    low = EngineState(rpm_ratio=0.2, throttle_ratio=0.2, map_ratio=0.3, fuel_flow_ratio=0.1)
    high = EngineState(rpm_ratio=0.7, throttle_ratio=0.8, map_ratio=0.9, fuel_flow_ratio=0.5)

    low_features = extractor.extract([low]).features
    high_features = extractor.extract([high]).features

    assert high_features["rpm_ratio"] > low_features["rpm_ratio"]
    assert high_features["throttle_ratio"] > low_features["throttle_ratio"]
    assert high_features["map_ratio"] > low_features["map_ratio"]
    assert high_features["fuel_flow_ratio"] > low_features["fuel_flow_ratio"]


def test_isolation_forest_detector_is_deterministic_and_detects_outlier():
    vectors = [FeatureVector(names=("x", "y"), values=(float(index), float(index))) for index in range(20)]
    abnormal = FeatureVector(names=("x", "y"), values=(100.0, 100.0))
    first = IsolationForestDetector(random_state=11)
    second = IsolationForestDetector(random_state=11)

    first.fit(vectors)
    second.fit(vectors)

    assert first.predict(abnormal)
    assert first.score(abnormal) > 0.0
    assert first.score(abnormal) == second.score(abnormal)
    assert first.predict(vectors[10]) is False


def test_isolation_forest_requires_fit_and_rejects_empty_data():
    detector = IsolationForestDetector()
    with pytest.raises(ValueError):
        detector.fit([])
    with pytest.raises(RuntimeError):
        detector.predict(FeatureVector(names=("x",), values=(1.0,)))


def test_baseline_diagnosis_has_structured_valid_output():
    state = EngineState(egt_rate=150.0, cht_rate=80.0, timestamp=BASE_TIME)
    diagnoses = BaselineFaultDiagnoser().diagnose([state], AnomalyResult(is_anomaly=True, score=0.8))

    assert diagnoses[0].fault_type.value == "OVERHEATING"
    assert 0.0 <= diagnoses[0].confidence <= 1.0
    assert 0.0 <= diagnoses[0].severity <= 1.0
    assert diagnoses[0].evidence


def test_sensor_detector_distinguishes_stuck_sensor():
    states = [EngineState(timestamp=BASE_TIME + timedelta(seconds=index), rpm=1000.0) for index in range(3)]
    statuses = BaselineSensorAnomalyDetector().inspect(states)
    rpm_status = next(status for status in statuses if status.sensor_name == "rpm")

    assert rpm_status.status is SensorCondition.STUCK
    assert 0.0 <= rpm_status.confidence <= 1.0
    assert 0.0 <= rpm_status.anomaly_score <= 1.0


def test_degradation_and_rul_are_honest_baselines():
    states = [EngineState(timestamp=BASE_TIME, overall_health=100.0), EngineState(timestamp=BASE_TIME, overall_health=70.0)]
    degradation = BaselineDegradationEstimator().estimate(states)
    rul_empty = UnavailableRULPredictor().predict([])
    rul_with_data = UnavailableRULPredictor().predict(states)

    assert 0.0 <= degradation.degradation_index <= 1.0
    assert degradation.trend is DegradationTrend.WORSENING
    assert rul_empty.status is RULStatus.INSUFFICIENT_DATA
    assert rul_with_data.status is RULStatus.NOT_TRAINED
    assert rul_with_data.estimated_remaining_time is None


def test_complete_analytics_pipeline_contract():
    simulator = SyntheticEngineSimulator(throttle=20.0)
    injector = FaultInjector(FaultType.OVERHEATING)
    twin = DigitalTwin(PistonEngineModel())
    states = []
    for _ in range(6):
        twin.ingest(injector.inject(simulator.step(0.1)))
        states.append(twin.update(0.1))

    vector = WindowFeatureExtractor().extract(states)
    anomaly = AnomalyResult(is_anomaly=False, score=0.0, timestamp=states[-1].timestamp)
    result = AnalyticsResult(
        anomaly=anomaly,
        fault_diagnoses=BaselineFaultDiagnoser().diagnose(states, anomaly),
        sensor_statuses=BaselineSensorAnomalyDetector().inspect(states),
        degradation=BaselineDegradationEstimator().estimate(states),
        rul=UnavailableRULPredictor().predict(states),
        timestamp=states[-1].timestamp,
    )

    assert vector.values
    assert result.anomaly is not None
    assert result.fault_diagnoses
    assert result.sensor_statuses
    assert result.degradation is not None
    assert result.rul is not None
