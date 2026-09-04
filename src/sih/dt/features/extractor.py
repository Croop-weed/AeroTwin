from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
import math

from sih.dt.core.state import EngineState
from sih.dt.features.schema import FeatureVector


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
