from __future__ import annotations

from dataclasses import dataclass

@dataclass
class ResidualWindow:
    """
    Contract object emitted by the Anomaly layer and consumed by the Fault Detection layer.
    This guarantees that the fault classifier only processes windows flagged as anomalous.
    """
    start_time: float
    end_time: float
    channel_residuals: dict[str, float]   # per-sensor residual (expected - actual)
    anomaly_score: float
    is_anomalous: bool                    # thresholded flag from the anomaly model
