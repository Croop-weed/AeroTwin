from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import random

from sih.dt.core.state import EngineState
from sih.dt.core.twin import DigitalTwin
from sih.dt.features.extractor import WindowFeatureExtractor
from sih.dt.features.schema import FeatureVector
from sih.dt.models.piston import PistonEngineModel
from sih.dt.simulation.engine import SyntheticEngineSimulator
from sih.dt.simulation.faults import FaultInjector, FaultType


class DatasetLabel(str, Enum):
    NORMAL = "NORMAL"
    OVERHEATING = FaultType.OVERHEATING.value
    LUBRICATION_FAILURE = FaultType.LUBRICATION_FAILURE.value
    INJECTOR_DEGRADATION = FaultType.INJECTOR_DEGRADATION.value
    MISFIRE = FaultType.MISFIRE.value
    COMBUSTION_INSTABILITY = FaultType.COMBUSTION_INSTABILITY.value
    ABNORMAL_VIBRATION = FaultType.ABNORMAL_VIBRATION.value
    SENSOR_DRIFT = FaultType.SENSOR_DRIFT.value
    SENSOR_FAILURE = FaultType.SENSOR_FAILURE.value

    @classmethod
    def from_fault_type(cls, fault_type: FaultType) -> DatasetLabel:
        return cls(fault_type.value)


@dataclass(frozen=True)
class GeneratedWindow:
    """One labelled feature window; run identity prevents accidental split leakage."""

    features: FeatureVector
    label: DatasetLabel
    run_id: str
    window_start: int
    window_end: int
    timestamp: datetime | None


@dataclass(frozen=True)
class FaultDataset:
    samples: tuple[GeneratedWindow, ...]

    @property
    def feature_names(self) -> tuple[str, ...]:
        return self.samples[0].features.names if self.samples else WindowFeatureExtractor().feature_names

    @property
    def labels(self) -> tuple[DatasetLabel, ...]:
        return tuple(sample.label for sample in self.samples)

    @property
    def run_ids(self) -> tuple[str, ...]:
        return tuple(sample.run_id for sample in self.samples)

    def to_arrays(self) -> tuple[list[list[float]], list[str]]:
        """Return ordinary numeric rows and labels accepted by sklearn estimators."""
        return (
            [sample.features.to_list() for sample in self.samples],
            [sample.label.value for sample in self.samples],
        )

    def __len__(self) -> int:
        return len(self.samples)


class FaultDatasetGenerator:
    """Generate coherent, labelled prototype engine windows.

    The simulator remains responsible for telemetry relationships. Timestamps are
    made deterministic here so a fixed seed produces repeatable feature windows.
    The resulting data is synthetic research data, not calibrated aircraft data.
    """

    def __init__(
        self,
        extractor: WindowFeatureExtractor | None = None,
        timestep_seconds: float = 0.1,
        seed: int | None = None,
    ) -> None:
        if timestep_seconds <= 0:
            raise ValueError("timestep_seconds must be positive")
        self.extractor = extractor or WindowFeatureExtractor()
        self.timestep_seconds = timestep_seconds
        self.seed = seed

    def _validate_shape(self, num_runs: int, steps_per_run: int, window_size: int, stride: int) -> None:
        if num_runs <= 0 or steps_per_run <= 0 or window_size <= 0 or stride <= 0:
            raise ValueError("run, step, window, and stride values must be positive")
        if window_size > steps_per_run:
            raise ValueError("window_size cannot exceed steps_per_run")

    def _run_states(
        self,
        run_id: str,
        label: DatasetLabel,
        steps_per_run: int,
        rng: random.Random,
    ) -> list[EngineState]:
        initial_throttle = rng.choice((10.0, 25.0, 45.0, 70.0))
        simulator = SyntheticEngineSimulator(throttle=initial_throttle)
        simulator.set_throttle(initial_throttle)
        twin = DigitalTwin(PistonEngineModel())
        injector = FaultInjector(None if label is DatasetLabel.NORMAL else FaultType(label.value))
        start = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=rng.randrange(365))
        states: list[EngineState] = []

        for step in range(steps_per_run):
            if step in (steps_per_run // 3, (2 * steps_per_run) // 3):
                simulator.set_throttle(rng.choice((15.0, 35.0, 55.0, 80.0)))
            telemetry = simulator.step(self.timestep_seconds)
            telemetry = telemetry.model_copy(
                update={
                    "timestamp": start + timedelta(seconds=step * self.timestep_seconds),
                }
            )
            twin.ingest(injector.inject(telemetry))
            states.append(twin.update(self.timestep_seconds))
        return states

    def _windows(
        self,
        states: Sequence[EngineState],
        label: DatasetLabel,
        run_id: str,
        window_size: int,
        stride: int,
    ) -> list[GeneratedWindow]:
        windows: list[GeneratedWindow] = []
        for start in range(0, len(states) - window_size + 1, stride):
            end = start + window_size
            state_window = states[start:end]
            windows.append(
                GeneratedWindow(
                    features=self.extractor.extract(state_window),
                    label=label,
                    run_id=run_id,
                    window_start=start,
                    window_end=end,
                    timestamp=state_window[-1].timestamp,
                )
            )
        return windows

    def _generate_runs(
        self,
        label: DatasetLabel,
        num_runs: int,
        steps_per_run: int,
        window_size: int,
        stride: int,
    ) -> FaultDataset:
        self._validate_shape(num_runs, steps_per_run, window_size, stride)
        rng = random.Random(self.seed)
        samples: list[GeneratedWindow] = []
        for run_number in range(num_runs):
            run_id = f"{label.value.lower()}-{run_number:04d}"
            states = self._run_states(run_id, label, steps_per_run, rng)
            samples.extend(self._windows(states, label, run_id, window_size, stride))
        return FaultDataset(tuple(samples))

    def generate_normal(
        self,
        num_runs: int = 4,
        steps_per_run: int = 30,
        window_size: int = 10,
        stride: int = 1,
    ) -> FaultDataset:
        return self._generate_runs(DatasetLabel.NORMAL, num_runs, steps_per_run, window_size, stride)

    def generate_fault(
        self,
        fault_type: FaultType,
        num_runs: int = 2,
        steps_per_run: int = 30,
        window_size: int = 10,
        stride: int = 1,
    ) -> FaultDataset:
        return self._generate_runs(DatasetLabel.from_fault_type(fault_type), num_runs, steps_per_run, window_size, stride)

    def generate(
        self,
        fault_types: Sequence[FaultType] = tuple(FaultType),
        normal_runs: int = 4,
        fault_runs: int = 2,
        steps_per_run: int = 30,
        window_size: int = 10,
        stride: int = 1,
    ) -> FaultDataset:
        datasets = [self.generate_normal(normal_runs, steps_per_run, window_size, stride)]
        for fault_type in fault_types:
            datasets.append(self.generate_fault(fault_type, fault_runs, steps_per_run, window_size, stride))
        return FaultDataset(tuple(sample for dataset in datasets for sample in dataset.samples))
