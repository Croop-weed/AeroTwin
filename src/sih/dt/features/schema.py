from __future__ import annotations

from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import Iterator, Mapping, Sequence


@dataclass(frozen=True)
class FeatureVector:
    """Ordered, finite numeric features independent of any ML library."""

    names: tuple[str, ...]
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.names) != len(self.values):
            raise ValueError("Feature names and values must have the same length")
        if len(set(self.names)) != len(self.names):
            raise ValueError("Feature names must be unique")
        if any(not math.isfinite(value) for value in self.values):
            raise ValueError("Feature values must be finite")

    @property
    def features(self) -> Mapping[str, float]:
        return MappingProxyType(dict(zip(self.names, self.values)))

    def as_dict(self) -> dict[str, float]:
        return dict(zip(self.names, self.values))

    def to_list(self) -> list[float]:
        return list(self.values)

    def __len__(self) -> int:
        return len(self.values)

    def __iter__(self) -> Iterator[float]:
        return iter(self.values)

    def __getitem__(self, index: int) -> float:
        return self.values[index]

    @classmethod
    def from_mapping(cls, features: Mapping[str, float]) -> FeatureVector:
        names = tuple(features)
        values = tuple(float(features[name]) for name in names)
        return cls(names=names, values=values)


def feature_matrix(vectors: Sequence[FeatureVector]) -> list[list[float]]:
    """Convert compatible vectors to rows suitable for any numeric model."""
    if not vectors:
        return []
    names = vectors[0].names
    if any(vector.names != names for vector in vectors):
        raise ValueError("Feature vectors must have identical ordered names")
    return [vector.to_list() for vector in vectors]
