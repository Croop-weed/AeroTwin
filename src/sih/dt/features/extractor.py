from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
import math

from sih.dt.core.state import EngineState
from sih.dt.features.schema import FeatureVector, RESIDUAL_CHANNELS
from sih.dt.features.physics import PhysicsReferenceModel


class WindowFeatureExtractor:
    """Compact descriptive features for one EngineState time window.

    Statistics describe observed values. They are not calibrated expected engine
    values and should not be treated as a physical model.
    """

    STAT_FIELDS = (
        "rpm",
        "throttle",
        "manifold_absolute_pressure",
        "egt",
        "cht",
        "oil_pressure",
        "oil_temperature",
        "fuel_flow",
        "vibration",
        "battery_voltage",
        "injection_timing_deg",
    )
    TREND_FIELDS = ("rpm", "egt", "cht", "oil_temperature", "vibration", "fuel_flow")
    CONDITION_FIELDS = ("rpm_ratio", "throttle_ratio", "map_ratio", "fuel_flow_ratio")

    @property
    def feature_names(self) -> tuple[str, ...]:
        names: list[str] = []
        for field in self.STAT_FIELDS:
            names.extend((f"{field}_mean", f"{field}_std", f"{field}_min", f"{field}_max"))
        names.extend(f"{field}_slope" for field in self.TREND_FIELDS)
        names.extend(self.CONDITION_FIELDS)
        return tuple(names)

    @staticmethod
    def _finite(value: float) -> float:
        return float(value) if math.isfinite(float(value)) else 0.0

    def _values(self, states: Sequence[EngineState], field: str) -> list[float]:
        return [self._finite(getattr(state, field)) for state in states]

    def _slope(self, states: Sequence[EngineState], field: str) -> float:
        if len(states) < 2:
            return 0.0
        values = self._values(states, field)
        timestamps = [state.timestamp for state in states]
        if any(timestamp is None for timestamp in timestamps):
            return 0.0
        timestamp_values = [timestamp for timestamp in timestamps if timestamp is not None]
        first_timestamp = timestamp_values[0]
        assert isinstance(first_timestamp, datetime)
        times = [self._finite((timestamp - first_timestamp).total_seconds()) for timestamp in timestamp_values]
        mean_time = sum(times) / len(times)
        mean_value = sum(values) / len(values)
        denominator = sum((time - mean_time) ** 2 for time in times)
        if denominator <= 0.0:
            return 0.0
        return self._finite(sum((time - mean_time) * (value - mean_value) for time, value in zip(times, values)) / denominator)

    def extract(self, states: Sequence[EngineState]) -> FeatureVector:
        values: list[float] = []
        for field in self.STAT_FIELDS:
            field_values = self._values(states, field)
            if not field_values:
                field_values = [0.0]
            mean = sum(field_values) / len(field_values)
            variance = sum((value - mean) ** 2 for value in field_values) / len(field_values)
            values.extend((mean, math.sqrt(variance), min(field_values), max(field_values)))
        values.extend(self._slope(states, field) for field in self.TREND_FIELDS)
        for field in self.CONDITION_FIELDS:
            current = self._finite(getattr(states[-1], field)) if states else 0.0
            values.append(current)
        return FeatureVector(names=self.feature_names, values=tuple(self._finite(value) for value in values))


class ResidualFeatureExtractor:
    """Extracts features by comparing actual values to a reference model and calculating statistics on the residuals."""
    
    def __init__(self, reference_model: PhysicsReferenceModel):
        self.reference_model = reference_model

    @staticmethod
    def _finite(value: float) -> float:
        return float(value) if math.isfinite(float(value)) else 0.0

    def _slope(self, times: list[float], residuals: list[float]) -> float:
        if len(times) < 2:
            return 0.0
        mean_time = sum(times) / len(times)
        mean_value = sum(residuals) / len(residuals)
        denominator = sum((time - mean_time) ** 2 for time in times)
        if denominator <= 0.0:
            return 0.0
        return self._finite(sum((time - mean_time) * (value - mean_value) for time, value in zip(times, residuals)) / denominator)

    def extract(self, states: Sequence[EngineState]) -> FeatureVector:
        if not states:
            return FeatureVector(names=(), values=())

        timestamps = [state.timestamp for state in states]
        if any(t is None for t in timestamps):
            times = [0.0] * len(states) # Fallback if no timestamps
        else:
            first = timestamps[0]
            assert isinstance(first, datetime)
            times = [self._finite((t - first).total_seconds()) for t in timestamps if t is not None]

        names: list[str] = []
        values: list[float] = []

        # We compute expected states once per state
        expected_states = [self.reference_model.expected_state(state) for state in states]

        for channel in RESIDUAL_CHANNELS:
            channel_residuals: list[float] = []
            for state, expected in zip(states, expected_states):
                actual_val = getattr(state, channel, 0.0)
                expected_val = getattr(expected, channel, 0.0)
                channel_residuals.append(actual_val - expected_val)

            mean_res = sum(channel_residuals) / len(channel_residuals)
            variance_res = sum((v - mean_res) ** 2 for v in channel_residuals) / len(channel_residuals)
            std_res = math.sqrt(variance_res)
            max_abs_res = max(abs(v) for v in channel_residuals)
            slope_res = self._slope(times, channel_residuals)

            names.extend([
                f"{channel}_residual_mean",
                f"{channel}_residual_std",
                f"{channel}_residual_max_abs",
                f"{channel}_residual_slope"
            ])
            values.extend([mean_res, std_res, max_abs_res, slope_res])

        return FeatureVector(names=tuple(names), values=tuple(self._finite(value) for value in values))
