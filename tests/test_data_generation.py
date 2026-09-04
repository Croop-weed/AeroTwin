from collections import Counter
import math

import pytest

from sih.dt.data import DatasetLabel, FaultDatasetGenerator
from sih.dt.simulation.faults import FaultType


def test_normal_dataset_generation_preserves_runs_and_windows():
	dataset = FaultDatasetGenerator(seed=7).generate_normal(
		num_runs=2,
		steps_per_run=12,
		window_size=4,
		stride=2,
	)

	assert len(dataset) == 10
	assert set(dataset.labels) == {DatasetLabel.NORMAL}
	assert len(set(dataset.run_ids)) == 2
	assert all(sample.window_end - sample.window_start == 4 for sample in dataset.samples)


def test_fault_dataset_generation_uses_typed_correct_labels():
	dataset = FaultDatasetGenerator(seed=4).generate_fault(
		FaultType.OVERHEATING,
		num_runs=2,
		steps_per_run=10,
		window_size=5,
	)

	assert len(dataset) == 12
	assert set(dataset.labels) == {DatasetLabel.OVERHEATING}
	assert all(sample.run_id.startswith("overheating-") for sample in dataset.samples)


def test_multiple_fault_classes_are_supported():
	dataset = FaultDatasetGenerator(seed=3).generate(
		fault_types=(FaultType.OVERHEATING, FaultType.MISFIRE, FaultType.SENSOR_FAILURE),
		normal_runs=1,
		fault_runs=1,
		steps_per_run=8,
		window_size=4,
		stride=4,
	)

	assert set(dataset.labels) == {
		DatasetLabel.NORMAL,
		DatasetLabel.OVERHEATING,
		DatasetLabel.MISFIRE,
		DatasetLabel.SENSOR_FAILURE,
	}
	assert Counter(dataset.labels) == Counter({label: 2 for label in set(dataset.labels)})


def test_feature_dimensions_and_values_are_ml_ready():
	dataset = FaultDatasetGenerator(seed=8).generate(
		fault_types=(FaultType.LUBRICATION_FAILURE,),
		normal_runs=1,
		fault_runs=1,
		steps_per_run=12,
		window_size=6,
	)
	matrix, labels = dataset.to_arrays()

	assert len(matrix) == len(labels) == len(dataset)
	assert all(len(row) == len(dataset.feature_names) for row in matrix)
	assert all(math.isfinite(value) for row in matrix for value in row)
	assert labels[0] == DatasetLabel.NORMAL.value


def test_seeded_generation_is_deterministic():
	first = FaultDatasetGenerator(seed=99).generate(
		fault_types=(FaultType.INJECTOR_DEGRADATION,),
		normal_runs=1,
		fault_runs=1,
		steps_per_run=10,
		window_size=5,
	)
	second = FaultDatasetGenerator(seed=99).generate(
		fault_types=(FaultType.INJECTOR_DEGRADATION,),
		normal_runs=1,
		fault_runs=1,
		steps_per_run=10,
		window_size=5,
	)

	assert first == second


def test_windows_contain_temporal_information():
	dataset = FaultDatasetGenerator(seed=2).generate_normal(
		num_runs=1,
		steps_per_run=12,
		window_size=6,
	)

	slopes = [sample.features.features["rpm_slope"] for sample in dataset.samples]
	assert any(abs(slope) > 0.0 for slope in slopes)
	assert all(sample.timestamp is not None for sample in dataset.samples)


def test_generator_rejects_invalid_window_shapes():
	with pytest.raises(ValueError):
		FaultDatasetGenerator().generate_normal(steps_per_run=3, window_size=4)
