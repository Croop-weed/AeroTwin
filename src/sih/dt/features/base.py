from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sih.dt.core.state import EngineState
from sih.dt.features.schema import FeatureVector


class FeatureExtractor(Protocol):
    def extract(self, states: Sequence[EngineState]) -> FeatureVector:
        """Convert an EngineState window into model-independent features."""
