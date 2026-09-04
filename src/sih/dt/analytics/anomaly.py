from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sklearn.ensemble import IsolationForest

from sih.dt.analytics.base import AnomalyDetector
from sih.dt.features.schema import FeatureVector, feature_matrix


class AnomalyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_anomaly: bool
    score: float
    timestamp: datetime | None = None


class IsolationForestDetector:
    """Isolation Forest adapter; engine and feature models remain ML-agnostic."""

    def __init__(self, contamination: float | str = "auto", random_state: int | None = None) -> None:
        self.contamination = contamination
        self.random_state = random_state
        self._model: IsolationForest | None = None
        self._feature_names: tuple[str, ...] | None = None

    def fit(self, vectors: Sequence[FeatureVector]) -> None:
        if not vectors:
            raise ValueError("At least one normal feature vector is required")
        self._feature_names = vectors[0].names
        self._model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
        )
        self._model.fit(feature_matrix(vectors))

    def _require_model(self, vector: FeatureVector) -> IsolationForest:
        if self._model is None or self._feature_names is None:
            raise RuntimeError("Detector must be fitted before prediction")
        if vector.names != self._feature_names:
            raise ValueError("Feature vector names do not match fitted features")
        return self._model

    def predict(self, vector: FeatureVector) -> bool:
        return bool(self._require_model(vector).predict([vector.to_list()])[0] == -1)

    def score(self, vector: FeatureVector) -> float:
        model = self._require_model(vector)
        return float(-model.score_samples([vector.to_list()])[0])

    def predict_many(self, vectors: Sequence[FeatureVector]) -> list[bool]:
        return [self.predict(vector) for vector in vectors]

    def score_many(self, vectors: Sequence[FeatureVector]) -> list[float]:
        return [self.score(vector) for vector in vectors]


__all__ = ["AnomalyDetector", "AnomalyResult", "IsolationForestDetector"]
