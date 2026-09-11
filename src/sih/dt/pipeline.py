import os
import time
import torch
import torch.nn as nn
import numpy as np
from datetime import datetime

from sih.dt.data.generator import FaultDatasetGenerator
from sih.dt.simulation.faults import FaultType
from sih.dt.analytics.anomaly import IsolationForestDetector
from sih.dt.analytics.contracts import ResidualWindow
from sih.dt.features.schema import RESIDUAL_CHANNELS
from sih.dt.features.extractor import ResidualFeatureExtractor
from sih.dt.features.physics import PhysicsReferenceModel

from sih.dt.analytics.rul_model import AeroTwinRULModel

# ---------------------------------------------------------
# WRAPPER CLASSES (From 01 and 02 scripts)
# ---------------------------------------------------------
class RULEstimator:
    def __init__(self, model: AeroTwinRULModel):
        self.model = model
        self.model.freeze_shared_core()
        self.optimizer = torch.optim.Adam(self.model.sim_encoder.parameters(), lr=1e-3)
        self.criterion = nn.MSELoss()
        
    def fine_tune_and_predict(self, history: list[list[float]], true_rul: float) -> float:
        if len(history) < 30:
            return 999.0
        window = history[-30:]
        x_tensor = torch.tensor(window, dtype=torch.float32).unsqueeze(0)
        y_true = torch.tensor([[true_rul]], dtype=torch.float32)
        
        self.model.train()
        for _ in range(5):  # Option A: Aggressive live fine-tuning
            self.optimizer.zero_grad()
            pred = self.model.forward_sim(x_tensor)
            loss = self.criterion(pred, y_true)
            loss.backward()
            self.optimizer.step()
        
        self.model.eval()
        with torch.no_grad():
            final_pred = self.model.forward_sim(x_tensor).item()
        return final_pred

from sklearn.ensemble import RandomForestClassifier

class VibrationFaultClassifier:
    def __init__(self):
        self.clf = RandomForestClassifier(n_estimators=50, random_state=42)
    def fit_dummy(self, X: np.ndarray, y: np.ndarray) -> None:
        self.clf.fit(X, y)
    def predict(self, residual_window: ResidualWindow) -> str | None:
        X = np.array([[
            residual_window.channel_residuals.get("vibration_residual_mean", 0.0),
            residual_window.channel_residuals.get("vibration_residual_std", 0.0),
            residual_window.channel_residuals.get("vibration_residual_max_abs", 0.0),
            residual_window.channel_residuals.get("vibration_residual_slope", 0.0),
        ]]) 
        return str(self.clf.predict(X)[0])

class TabularFaultClassifier:
    def __init__(self):
        self.clf = RandomForestClassifier(n_estimators=50, random_state=42)
    def fit_dummy(self, X: np.ndarray, y: np.ndarray) -> None:
        self.clf.fit(X, y)
    def predict(self, residual_window: ResidualWindow) -> str | None:
        features = []
        for channel in ["egt", "oil_pressure", "fuel_flow"]:
            features.extend([
                residual_window.channel_residuals.get(f"{channel}_residual_mean", 0.0),
                residual_window.channel_residuals.get(f"{channel}_residual_std", 0.0),
                residual_window.channel_residuals.get(f"{channel}_residual_max_abs", 0.0),
                residual_window.channel_residuals.get(f"{channel}_residual_slope", 0.0),
            ])
        X = np.array([features]) 
        return str(self.clf.predict(X)[0])

def detect_sensor_drift(residual_window: ResidualWindow) -> bool:
    egt_res_mean = residual_window.channel_residuals.get("egt_residual_mean", 0.0)
    egt_res_slope = residual_window.channel_residuals.get("egt_residual_slope", 0.0)
    if egt_res_mean > 20.0 and abs(egt_res_slope) > 0.5:
        return True
    return False

# ---------------------------------------------------------
# MASTER PIPELINE
# ---------------------------------------------------------
# REUSABLE PIPELINE MODEL FACTORIES & CALIBRATORS
# ---------------------------------------------------------
def load_rul_estimator(cache_path: str = "data/cache/best_rul_model.pth") -> RULEstimator | None:
    """Loads the pretrained Dual-Encoder LSTM model and returns a RULEstimator."""
    if not os.path.exists(cache_path):
        return None
    rul_model = AeroTwinRULModel(cmapss_dim=14, sim_dim=6)
    rul_model.load_state_dict(torch.load(cache_path, weights_only=True))
    return RULEstimator(rul_model)


def calibrate_anomaly_detector(
    generator: FaultDatasetGenerator | None = None,
    num_runs: int = 20,
    steps_per_run: int = 150,
) -> tuple[IsolationForestDetector, FaultDatasetGenerator, any]:
    """Calibrates an IsolationForestDetector on normal flight windows."""
    if generator is None:
        reference_model = PhysicsReferenceModel()
        extractor = ResidualFeatureExtractor(reference_model)
        generator = FaultDatasetGenerator(seed=None, extractor=extractor)

    ds_norm = generator.generate_normal(num_runs=num_runs, steps_per_run=steps_per_run)
    detector = IsolationForestDetector(contamination=0.05, random_state=None)
    normal_vectors = [sample.features for sample in ds_norm.samples]
    detector.fit(normal_vectors)
    return detector, generator, ds_norm


def calibrate_fault_classifiers(
    generator: FaultDatasetGenerator,
    ds_norm: any,
    num_runs: int = 5,
    steps_per_run: int = 20,
) -> tuple[VibrationFaultClassifier, TabularFaultClassifier]:
    """Calibrates vibration and tabular fault classifiers using synthetic runs."""
    ds_vib = generator.generate_fault(FaultType.ABNORMAL_VIBRATION, num_runs=num_runs, steps_per_run=steps_per_run)
    ds_misfire = generator.generate_fault(FaultType.MISFIRE, num_runs=num_runs, steps_per_run=steps_per_run)
    ds_comb = generator.generate_fault(FaultType.COMBUSTION_INSTABILITY, num_runs=num_runs, steps_per_run=steps_per_run)

    X_vib_list, y_vib_list = [], []
    for ds, label in [
        (ds_norm, "NORMAL"),
        (ds_vib, FaultType.ABNORMAL_VIBRATION.value),
        (ds_misfire, FaultType.MISFIRE.value),
        (ds_comb, FaultType.COMBUSTION_INSTABILITY.value),
    ]:
        for sample in ds.samples:
            vec = sample.features
            X_vib_list.append([
                vec.features.get("vibration_residual_mean", 0.0),
                vec.features.get("vibration_residual_std", 0.0),
                vec.features.get("vibration_residual_max_abs", 0.0),
                vec.features.get("vibration_residual_slope", 0.0),
            ])
            y_vib_list.append(label)

    vib_clf = VibrationFaultClassifier()
    vib_clf.fit_dummy(np.array(X_vib_list), np.array(y_vib_list))

    ds_over = generator.generate_fault(FaultType.OVERHEATING, num_runs=num_runs, steps_per_run=steps_per_run)
    ds_lube = generator.generate_fault(FaultType.LUBRICATION_FAILURE, num_runs=num_runs, steps_per_run=steps_per_run)

    X_tab_list, y_tab_list = [], []
    for ds, label in [
        (ds_norm, "NORMAL"),
        (ds_over, FaultType.OVERHEATING.value),
        (ds_lube, FaultType.LUBRICATION_FAILURE.value),
    ]:
        for sample in ds.samples:
            vec = sample.features
            feats = []
            for channel in ["egt", "oil_pressure", "fuel_flow"]:
                feats.extend([
                    vec.features.get(f"{channel}_residual_mean", 0.0),
                    vec.features.get(f"{channel}_residual_std", 0.0),
                    vec.features.get(f"{channel}_residual_max_abs", 0.0),
                    vec.features.get(f"{channel}_residual_slope", 0.0),
                ])
            X_tab_list.append(feats)
            y_tab_list.append(label)

    tab_clf = TabularFaultClassifier()
    tab_clf.fit_dummy(np.array(X_tab_list), np.array(y_tab_list))

    return vib_clf, tab_clf


def setup_pipeline_models(cache_path: str = "data/cache/best_rul_model.pth", fast: bool = False):
    """Convenience setup that initializes and calibrates all pipeline models."""
    rul_estimator = load_rul_estimator(cache_path)
    norm_runs = 3 if fast else 20
    norm_steps = 30 if fast else 150
    fault_runs = 2 if fast else 5
    fault_steps = 15 if fast else 20

    detector, generator, ds_norm = calibrate_anomaly_detector(num_runs=norm_runs, steps_per_run=norm_steps)
    vib_clf, tab_clf = calibrate_fault_classifiers(
        generator, ds_norm, num_runs=fault_runs, steps_per_run=fault_steps
    )
    return {
        "rul_estimator": rul_estimator,
        "detector": detector,
        "generator": generator,
        "vib_clf": vib_clf,
        "tab_clf": tab_clf,
    }


# ---------------------------------------------------------
# MASTER PIPELINE
# ---------------------------------------------------------
def main():
    print("==================================================")
    print("   AeroTwin: End-to-End Digital Twin Pipeline     ")
    print("==================================================\n")

    # 1. SETUP: Load LSTM
    print("[1/3] Loading Pretrained Dual-Encoder LSTM...")
    model_cache_path = "data/cache/best_rul_model.pth"
    rul_estimator = load_rul_estimator(model_cache_path)
    if rul_estimator is not None:
        print("      -> Successfully loaded weights from NASA benchmark.")
    else:
        print("      -> WARNING: Cache not found. Run 01_ai_ml_layer.py to train it first!")
        return

    # 2. SETUP: Train Anomaly Detector
    print("[2/3] Training Anomaly Detector...")
    reference_model = PhysicsReferenceModel()
    extractor = ResidualFeatureExtractor(reference_model)
    generator = FaultDatasetGenerator(seed=None, extractor=extractor)

    detector, generator, ds_norm = calibrate_anomaly_detector(generator=generator, num_runs=20, steps_per_run=150)
    normal_vectors = [sample.features for sample in ds_norm.samples]
    print(f"      -> Isolation Forest calibrated on {len(normal_vectors)} healthy windows.")

    # 3. SETUP: Train Classifiers
    print("[3/3] Calibrating Fault Diagnostics...")
    vib_clf, tab_clf = calibrate_fault_classifiers(generator, ds_norm, num_runs=5, steps_per_run=20)
    print("      -> Classifiers ready.\n")
    
    # -----------------------------------------------------
    # LIVE SIMULATION
    # -----------------------------------------------------
    print("==================================================")
    print("   Initiating Live Flight Telemetry Simulation    ")
    print("==================================================\n")
    
    # We ask the generator to simulate a specific fault scenario (Overheating)
    test_ds = generator.generate_fault(FaultType.OVERHEATING, num_runs=1, steps_per_run=150)
    
    history_buffer = []
    true_rul_counter = 150
    anomaly_streak = 0  # Technique 2: Require 3 consecutive anomalies to trigger alarm
    
    for idx, sample in enumerate(test_ds.samples):
        # Simulate real-time streaming delay
        time.sleep(0.15)
        
        # 1. Evaluate Anomaly
        vec = sample.features
        is_anomalous = detector.predict(vec)
        score = detector.score(vec)
        
        # Build history for RUL
        residuals = []
        for channel in RESIDUAL_CHANNELS:
            residuals.append(vec.features.get(f"{channel}_residual_mean", 0.0))
        history_buffer.append(residuals)
        true_rul_counter = max(0, true_rul_counter - 1)
        
        if is_anomalous:
            anomaly_streak += 1
        else:
            anomaly_streak = 0
            
        # Extract a pseudo-sensor reading for the dashboard (using EGT residual as a proxy for temperature variance)
        egt_variance = vec.features.get("egt_residual_mean", 0.0)
        vib_variance = vec.features.get("vibration_residual_mean", 0.0)
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        # 2. Trigger Action if Degraded (Rolling Average Smoothing)
        if anomaly_streak >= 3:
            # We construct a real ResidualWindow
            channel_residuals = {k: v for k, v in vec.features.items() if "residual" in k}
            rw = ResidualWindow(
                start_time=float(sample.window_start),
                end_time=float(sample.window_end),
                channel_residuals=channel_residuals,
                anomaly_score=score,
                is_anomalous=True
            )
            
            # Predict RUL
            rul_pred = 999.0
            if len(history_buffer) >= 30:
                rul_pred = rul_estimator.fine_tune_and_predict(history_buffer, true_rul_counter)
                
            # Diagnose Fault
            diagnosis = "UNKNOWN"
            if detect_sensor_drift(rw):
                diagnosis = "SENSOR_DRIFT"
            else:
                tab_pred = tab_clf.predict(rw)
                vib_pred = vib_clf.predict(rw)
                if vib_pred != "NORMAL":
                    diagnosis = vib_pred
                elif tab_pred != "NORMAL":
                    diagnosis = tab_pred
                else:
                    diagnosis = "NORMAL"
                    
            print(f"[{now}] \033[91mCRITICAL\033[0m | Cycle {idx:03d} | Anomaly Detected! (Confidence: {score:.2f})")
            print(f"[{now}] \033[93mDIAGNOSIS\033[0m | Root Cause: {diagnosis}")
            if rul_pred != 999.0:
                print(f"[{now}] \033[95mPREDICTION\033[0m | Remaining Useful Life: {rul_pred:.1f} cycles (True: {true_rul_counter})")
            else:
                print(f"[{now}] \033[95mPREDICTION\033[0m | Remaining Useful Life: Calculating... (Awaiting history buffer)")
            print("-" * 80)
            
        else:
            # Print a realistic streaming log every cycle
            print(f"[{now}] \033[92mINFO\033[0m | Cycle {idx:03d} | EGT Var: {egt_variance:+.2f} | Vib Var: {vib_variance:+.2f} | Status: NOMINAL")

if __name__ == "__main__":
    main()
