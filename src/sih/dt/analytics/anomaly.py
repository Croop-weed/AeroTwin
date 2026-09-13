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


import pickle
import os

class IsolationForestDetector:
    """Isolation Forest adapter; engine and feature models remain ML-agnostic."""

    def __init__(self, contamination: float | str = "auto", random_state: int | None = None) -> None:
        self.contamination = contamination
        self.random_state = random_state
        self._model: IsolationForest | None = None
        self._scaler = None
        self._feature_names: tuple[str, ...] | None = None

    def save(self, path: str) -> None:
        if self._model is None or self._scaler is None or self._feature_names is None:
            raise RuntimeError("Detector must be fitted before saving")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        state = {
            "model": self._model,
            "scaler": self._scaler,
            "feature_names": self._feature_names,
            "contamination": self.contamination,
            "random_state": self.random_state
        }
        with open(path, "wb") as f:
            pickle.dump(state, f)

    @classmethod
    def load(cls, path: str) -> IsolationForestDetector:
        if not os.path.exists(path):
            raise FileNotFoundError(f"No saved model found at {path}")
        with open(path, "rb") as f:
            state = pickle.load(f)
        
        detector = cls(contamination=state["contamination"], random_state=state["random_state"])
        detector._model = state["model"]
        detector._scaler = state["scaler"]
        detector._feature_names = state["feature_names"]
        return detector

    def fit(self, vectors: Sequence[FeatureVector]) -> None:
        if not vectors:
            raise ValueError("At least one normal feature vector is required")
        self._feature_names = vectors[0].names
        from sklearn.preprocessing import StandardScaler
        
        self._scaler = StandardScaler()
        X = feature_matrix(vectors)
        X_scaled = self._scaler.fit_transform(X)
        
        self._model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
        )
        self._model.fit(X_scaled)

    def _require_model(self, vector: FeatureVector) -> tuple[IsolationForest, object]:
        if self._model is None or self._scaler is None or self._feature_names is None:
            raise RuntimeError("Detector must be fitted before prediction")
        if vector.names != self._feature_names:
            raise ValueError("Feature vector names do not match fitted features")
        return self._model, self._scaler

    def predict(self, vector: FeatureVector) -> bool:
        model, scaler = self._require_model(vector)
        X_scaled = scaler.transform([vector.to_list()])
        return bool(model.predict(X_scaled)[0] == -1)

    def score(self, vector: FeatureVector) -> float:
        model, scaler = self._require_model(vector)
        X_scaled = scaler.transform([vector.to_list()])
        return float(-model.score_samples(X_scaled)[0])

    def predict_many(self, vectors: Sequence[FeatureVector]) -> list[bool]:
        # Optimize by scaling in batch
        if not vectors:
            return []
        model, scaler = self._require_model(vectors[0])
        X_scaled = scaler.transform(feature_matrix(vectors))
        preds = model.predict(X_scaled)
        return [bool(p == -1) for p in preds]

    def score_many(self, vectors: Sequence[FeatureVector]) -> list[float]:
        if not vectors:
            return []
        model, scaler = self._require_model(vectors[0])
        X_scaled = scaler.transform(feature_matrix(vectors))
        scores = -model.score_samples(X_scaled)
        return [float(s) for s in scores]


__all__ = ["AnomalyDetector", "AnomalyResult", "IsolationForestDetector"]
