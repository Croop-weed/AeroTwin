from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sih.dt.features.schema import FeatureVector


class AnomalyDetector(Protocol):
    def fit(self, vectors: Sequence[FeatureVector]) -> None:
        """Fit on feature vectors representing normal operation."""

    def predict(self, vector: FeatureVector) -> bool:
        """Return whether one vector is anomalous."""

    def score(self, vector: FeatureVector) -> float:
        """Return a higher-is-more-anomalous score."""
