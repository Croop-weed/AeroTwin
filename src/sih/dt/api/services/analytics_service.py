from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
import logging
from typing import Any
import torch

from sih.dt.analytics.anomaly import AnomalyResult, IsolationForestDetector
from sih.dt.analytics.contracts import ResidualWindow
from sih.dt.analytics.degradation import BaselineDegradationEstimator, DegradationState
from sih.dt.analytics.diagnosis import BaselineFaultDiagnoser, FaultDiagnosis
from sih.dt.analytics.rul import RULPrediction, RULStatus, UnavailableRULPredictor
from sih.dt.analytics.sensor import BaselineSensorAnomalyDetector, SensorStatus
from sih.dt.api.schemas.analytics import (
    AnalyticsSummaryResponse,
    AnomalyResponse,
    DegradationResponse,
    FaultDiagnosisItem,
    RULResponse,
    SensorStatusItem,
)
from sih.dt.core.state import EngineState
from sih.dt.features.extractor import ResidualFeatureExtractor, WindowFeatureExtractor
from sih.dt.features.physics import PhysicsReferenceModel
from sih.dt.features.schema import RESIDUAL_CHANNELS
from sih.dt.pipeline import (
    RULEstimator,
    TabularFaultClassifier,
    VibrationFaultClassifier,
    detect_sensor_drift,
    load_rul_estimator,
    setup_pipeline_models,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Orchestrates Anomaly Detection, Fault Diagnosis, Degradation, RUL, and Sensor Health."""

    def __init__(
        self,
        rul_estimator: RULEstimator | None = None,
        anomaly_detector: IsolationForestDetector | None = None,
        vib_classifier: VibrationFaultClassifier | None = None,
        tab_classifier: TabularFaultClassifier | None = None,
    ) -> None:
        self.rul_estimator = rul_estimator
        self.anomaly_detector = anomaly_detector
        self.vib_classifier = vib_classifier
        self.tab_classifier = tab_classifier

        self.physics_ref = PhysicsReferenceModel()
        self.residual_extractor = ResidualFeatureExtractor(self.physics_ref)
        self.window_extractor = WindowFeatureExtractor()

        self.baseline_diagnoser = BaselineFaultDiagnoser()
        self.baseline_degradation = BaselineDegradationEstimator()
        self.baseline_sensor = BaselineSensorAnomalyDetector()
        self.unavailable_rul = UnavailableRULPredictor()

        self._models_ready = False

    def initialize_models(self, fast: bool = False, cache_path: str = "data/cache/best_rul_model_finetuned.pth") -> None:
        """Loads pretrained weights and calibrates models once during application startup."""
        try:
            logger.info("Initializing Analytics ML models (Dual-Encoder RUL, Isolation Forest, Classifiers)...")
            models = setup_pipeline_models(cache_path=cache_path, fast=fast)
            self.rul_estimator = models["rul_estimator"]
            self.anomaly_detector = models["detector"]
            self.vib_classifier = models["vib_clf"]
            self.tab_classifier = models["tab_clf"]
            self._models_ready = True
            logger.info("All Analytics ML models successfully loaded and calibrated.")
        except Exception as exc:
            logger.warning(f"Could not calibrate full ML models: {exc}. Using baseline analytics fallbacks.")
            self._models_ready = False

    @property
    def is_ready(self) -> bool:
        return self._models_ready or self.anomaly_detector is not None

    def evaluate(
        self,
        uav_id: str,
        states: Sequence[EngineState],
        residual_history: list[list[float]] | None = None,
    ) -> AnalyticsSummaryResponse:
        """Runs full analytics evaluation against a sequence of recent EngineStates."""
        if not states:
            now = datetime.now(timezone.utc)
            return AnalyticsSummaryResponse(
                uav_id=uav_id,
                timestamp=now,
                anomaly=AnomalyResponse(is_anomaly=False, score=0.0, timestamp=now),
                faults=[],
                degradation=DegradationResponse(degradation_index=0.0, confidence=0.0, trend="INSUFFICIENT_DATA", timestamp=now),
                rul=RULResponse(status="INSUFFICIENT_DATA", timestamp=now),
                sensors=[],
            )

        current_state = states[-1]
        now = current_state.timestamp or datetime.now(timezone.utc)

        # 1. Feature Extraction & Anomaly Detection
        is_anomaly = False
        anomaly_score = 0.0
        res_vector = None

        try:
            res_vector = self.residual_extractor.extract(states)
            if self.anomaly_detector is not None and len(res_vector) > 0:
                is_anomaly = bool(self.anomaly_detector.predict(res_vector))
                anomaly_score = float(self.anomaly_detector.score(res_vector))
        except Exception as exc:
            logger.debug(f"Anomaly detection error: {exc}")
            # Fallback: check extreme physical deviations
            if (
                current_state.cht > 210.0
                or current_state.egt > 780.0
                or current_state.oil_pressure < 15.0
                or current_state.vibration > 3.5
            ):
                is_anomaly = True
                anomaly_score = 0.8

        anomaly_res = AnomalyResponse(
            is_anomaly=is_anomaly,
            score=max(0.0, min(1.0, anomaly_score)),
            timestamp=now,
        )

        # 2. Fault Diagnosis
        fault_items: list[FaultDiagnosisItem] = []

        # A) ML Fault Classifiers (if anomalous and residual window available)
        if res_vector is not None:
            channel_residuals = {k: v for k, v in res_vector.features.items() if "residual" in k}
            rw = ResidualWindow(
                start_time=0.0,
                end_time=float(len(states)),
                channel_residuals=channel_residuals,
                anomaly_score=anomaly_score,
                is_anomalous=is_anomaly,
            )

            if detect_sensor_drift(rw):
                fault_items.append(
                    FaultDiagnosisItem(
                        fault_type="SENSOR_DRIFT",
                        confidence=0.9,
                        severity=0.7,
                        evidence={"drift_channel": "egt", "egt_res_mean": channel_residuals.get("egt_residual_mean", 0.0)},
                        timestamp=now,
                    )
                )
            else:
                vib_pred = self.vib_classifier.predict(rw) if self.vib_classifier else None
                tab_pred = self.tab_classifier.predict(rw) if self.tab_classifier else None

                if vib_pred and vib_pred != "NORMAL":
                    fault_items.append(
                        FaultDiagnosisItem(
                            fault_type=vib_pred,
                            confidence=0.88,
                            severity=0.85,
                            evidence={"source": "vibration_classifier", "score": anomaly_score},
                            timestamp=now,
                        )
                    )
                if tab_pred and tab_pred != "NORMAL":
                    fault_items.append(
                        FaultDiagnosisItem(
                            fault_type=tab_pred,
                            confidence=0.85,
                            severity=0.80,
                            evidence={"source": "tabular_classifier", "score": anomaly_score},
                            timestamp=now,
                        )
                    )

        # B) Baseline Diagnoser Fallback / Augment
        core_anomaly = AnomalyResult(is_anomaly=is_anomaly, score=anomaly_score, timestamp=now)
        baseline_diagnoses = self.baseline_diagnoser.diagnose(states, anomaly=core_anomaly)
        for bd in baseline_diagnoses:
            if not any(f.fault_type == bd.fault_type.value for f in fault_items):
                fault_items.append(
                    FaultDiagnosisItem(
                        fault_type=bd.fault_type.value,
                        confidence=bd.confidence,
                        severity=bd.severity,
                        evidence=bd.evidence,
                        timestamp=bd.timestamp or now,
                    )
                )

        # C) Specific synthetic sensor and electrical failure detection
        if current_state.battery_voltage <= 0.5 and not any(f.fault_type == "SENSOR_FAILURE" for f in fault_items):
            fault_items.append(
                FaultDiagnosisItem(
                    fault_type="SENSOR_FAILURE",
                    confidence=0.95,
                    severity=0.90,
                    evidence={"failed_sensor": "battery_voltage", "voltage": current_state.battery_voltage},
                    timestamp=now,
                )
            )

        if (
            current_state.fuel_flow > 22.0
            and current_state.egt > 650.0
            and not any(f.fault_type in ("INJECTOR_DEGRADATION", "INJECTOR_ABNORMALITY") for f in fault_items)
        ):
            fault_items.append(
                FaultDiagnosisItem(
                    fault_type="INJECTOR_DEGRADATION",
                    confidence=0.82,
                    severity=0.75,
                    evidence={"fuel_flow": current_state.fuel_flow, "egt": current_state.egt},
                    timestamp=now,
                )
            )


        # 3. Degradation Estimation
        deg_state = self.baseline_degradation.estimate(states)
        degradation_res = DegradationResponse(
            degradation_index=round(deg_state.degradation_index, 4),
            confidence=round(deg_state.confidence, 3),
            trend=deg_state.trend.value,
            timestamp=deg_state.timestamp or now,
        )

        # 4. RUL Prediction
        rul_res: RULResponse
        if self.rul_estimator is not None and residual_history and len(residual_history) >= 30:
            try:
                window = residual_history[-30:]
                x_tensor = torch.tensor(window, dtype=torch.float32).unsqueeze(0)
                self.rul_estimator.model.eval()
                with torch.no_grad():
                    pred_val = float(self.rul_estimator.model.forward_sim(x_tensor).item())
                rul_cycles = max(0.0, round(pred_val, 1))
                rul_res = RULResponse(
                    status=RULStatus.AVAILABLE.value,
                    remaining_useful_life=rul_cycles,
                    lower_bound=max(0.0, round(rul_cycles * 0.85, 1)),
                    upper_bound=round(rul_cycles * 1.15, 1),
                    confidence=0.85,
                    timestamp=now,
                )
            except Exception as exc:
                logger.debug(f"RUL inference error: {exc}")
                rul_pred = self.unavailable_rul.predict(states)
                rul_res = RULResponse(
                    status=rul_pred.status.value,
                    remaining_useful_life=None,
                    confidence=0.0,
                    timestamp=now,
                )
        else:
            rul_pred = self.unavailable_rul.predict(states)
            rul_res = RULResponse(
                status=rul_pred.status.value,
                remaining_useful_life=None,
                confidence=0.0,
                timestamp=now,
            )

        # 5. Sensor Health Assessment
        sensor_statuses_core = self.baseline_sensor.inspect(states)
        sensor_items = [
            SensorStatusItem(
                sensor_name=s.sensor_name,
                status=s.status.value,
                confidence=round(s.confidence, 3),
                anomaly_score=round(s.anomaly_score, 3),
                timestamp=s.timestamp or now,
            )
            for s in sensor_statuses_core
        ]

        return AnalyticsSummaryResponse(
            uav_id=uav_id,
            timestamp=now,
            anomaly=anomaly_res,
            faults=fault_items,
            degradation=degradation_res,
            rul=rul_res,
            sensors=sensor_items,
        )


_GLOBAL_ANALYTICS_SERVICE: AnalyticsService | None = None


def get_analytics_service() -> AnalyticsService:
    global _GLOBAL_ANALYTICS_SERVICE
    if _GLOBAL_ANALYTICS_SERVICE is None:
        _GLOBAL_ANALYTICS_SERVICE = AnalyticsService()
    return _GLOBAL_ANALYTICS_SERVICE
