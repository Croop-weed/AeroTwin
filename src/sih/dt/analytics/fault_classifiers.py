from __future__ import annotations

import warnings
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestClassifier

from sih.dt.data.generator import FaultDatasetGenerator
from sih.dt.simulation.faults import FaultType
from sih.dt.analytics.contracts import ResidualWindow
from sih.dt.features.extractor import ResidualFeatureExtractor
from sih.dt.features.physics import PhysicsReferenceModel
from sih.dt.data.loaders import load_ai4i, load_cwru

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GroupShuffleSplit
from sklearn.metrics import precision_score, recall_score, average_precision_score

def validate_against_cwru() -> None:
    """
    Validation hook for CWRU Bearing Dataset.
    
    NOTE ON VIBRATION: Our simulator currently only emits a 1Hz scalar proxy for vibration 
    (not a high-frequency waveform). Therefore, true CWRU-equivalent FFT analysis is 
    impossible on our synthetic data. Instead, we use rolling statistical features (variance, 
    rate-of-change) as a simplified proxy.
    
    This hook serves as a structural placeholder for where we would validate the true 
    FFT/vibration-feature pipeline if we had raw kHz waveform data, before applying it 
    to our simulator's injected vibration faults.
    """
    print("\n--- CWRU Validation Hook (Vibration Faults) ---")
    print("NOTE: Simulator vibration is scalar-only. Using rolling stats as a simplified proxy, not true FFT analysis.")
    results = load_cwru()
    if not results:
        print("CWRU data not found or loader unimplemented. Skipping validation step.")
    else:
        print(f"Loaded {len(results)} CWRU files.")
        
        X_all, y_all, groups = [], [], []
        
        for file_idx, (df, meta) in enumerate(results):
            if df.empty:
                continue
            
            col = df.columns[0]
            arr = df[col].values
            fault_type = meta.get('fault_type', 'unknown')
            
            # Segment into 1024-length windows
            window_size = 1024
            for i in range(0, len(arr) - window_size + 1, window_size):
                window = arr[i:i+window_size]
                
                # Compute time-domain stats
                mean_val = window.mean()
                std_val = window.std()
                max_abs_val = np.max(np.abs(window))
                rms_val = np.sqrt(np.mean(window**2))
                crest_factor = max_abs_val / (rms_val + 1e-8)
                
                # Compute frequency-domain features (FFT)
                fft_vals = np.abs(np.fft.rfft(window))
                peak_fft = np.max(fft_vals[1:]) if len(fft_vals) > 1 else 0.0 # ignore DC component
                energy_fft = np.sum(fft_vals**2)
                
                X_all.append([mean_val, std_val, max_abs_val, rms_val, crest_factor, peak_fft, energy_fft])
                y_all.append(fault_type)
                groups.append(file_idx) # Group by file
                
        if X_all:
            X_all = np.array(X_all)
            y_all = np.array(y_all)
            groups = np.array(groups)
            
            # File-based split
            gss = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=42)
            train_idx, test_idx = next(gss.split(X_all, y_all, groups))
            
            X_train, y_train = X_all[train_idx], y_all[train_idx]
            X_test, y_test = X_all[test_idx], y_all[test_idx]
            
            train_files = len(np.unique(groups[train_idx]))
            test_files = len(np.unique(groups[test_idx]))
            
            print(f"Split: train ({train_files} files / {len(X_train)} windows), test ({test_files} files / {len(X_test)} windows)")
            
            # Print per-class counts
            print("Per-class counts:")
            for c in np.unique(y_all):
                c_train_idx = [i for i, y in enumerate(y_train) if y == c]
                c_test_idx = [i for i, y in enumerate(y_test) if y == c]
                c_train_files = len(np.unique([groups[train_idx][i] for i in c_train_idx]))
                c_test_files = len(np.unique([groups[test_idx][i] for i in c_test_idx]))
                print(f"  - {c}: train ({c_train_files} files / {len(c_train_idx)} windows), test ({c_test_files} files / {len(c_test_idx)} windows)")
            
            clf = RandomForestClassifier(n_estimators=50, class_weight="balanced", random_state=42)
            clf.fit(X_train, y_train)
            
            # Since fault types might be multiple classes, we use macro averages if >2 classes
            if len(np.unique(y_test)) > 1:
                preds = clf.predict(X_test)
                prec = precision_score(y_test, preds, average='macro', zero_division=0)
                rec = recall_score(y_test, preds, average='macro', zero_division=0)
                print(f"CWRU Validation: Precision (macro) = {prec:.3f}, Recall (macro) = {rec:.3f}")
            else:
                print("CWRU Validation: Not enough classes in test set to evaluate.")
                
            # Save the trained model
            os.makedirs("models", exist_ok=True)
            joblib.dump(clf, "models/cwru_rf_model.pkl")
            print("Saved CWRU Random Forest model to models/cwru_rf_model.pkl")


def validate_against_ai4i() -> None:
    """
    Validation hook for AI4I 2020 Predictive Maintenance Dataset.
    
    This validates our Random Forest classification approach on multi-mode tabular faults 
    before testing it on our simulator's labels.
    """
    print("\n--- AI4I Validation Hook (Tabular Faults) ---")
    df = load_ai4i()
    if df.empty:
        print("AI4I data not found or loader unimplemented. Skipping validation step.")
    else:
        print(f"Loaded AI4I data (shape: {df.shape}).")
        
        y = df["machine_failure"].values
        # Drop label and failure subtype components
        drop_cols = ["machine_failure", "TWF", "HDF", "PWF", "OSF", "RNF"]
        drop_cols = [c for c in drop_cols if c in df.columns]
        X = df.drop(columns=drop_cols).values
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
        
        train_fails = np.sum(y_train)
        test_fails = np.sum(y_test)
        print(f"Split: train ({len(X_train)} rows, {train_fails} failures), test ({len(X_test)} rows, {test_fails} failures)")
        
        # Per-class counts
        print("Per-class counts:")
        for c, name in [(0, "Healthy"), (1, "Failure")]:
            c_train_cnt = np.sum(y_train == c)
            c_test_cnt = np.sum(y_test == c)
            print(f"  - {name}: train ({c_train_cnt} rows), test ({c_test_cnt} rows)")
            
        clf = RandomForestClassifier(n_estimators=50, class_weight="balanced", random_state=42)
        clf.fit(X_train, y_train)
        
        preds = clf.predict(X_test)
        probs = clf.predict_proba(X_test)[:, 1]
        
        prec = precision_score(y_test, preds, zero_division=0)
        rec = recall_score(y_test, preds, zero_division=0)
        pr_auc = average_precision_score(y_test, probs)
        
        print(f"AI4I Validation: Precision = {prec:.3f}, Recall = {rec:.3f}, PR-AUC = {pr_auc:.3f}")

class VibrationFaultClassifier:
    """
    Classifies vibration-based faults: Misfire, Combustion Instability, Abnormal Vibration.
    Uses simplified rolling stats proxy instead of true FFT due to scalar simulator data.
    """
    def __init__(self):
        self.clf = RandomForestClassifier(n_estimators=50, random_state=42)
        self.is_trained = False
        
    def fit_dummy(self, X: np.ndarray, y: np.ndarray) -> None:
        self.clf.fit(X, y)
        self.is_trained = True

    def predict(self, residual_window: ResidualWindow) -> str | None:
        if not self.is_trained:
            warnings.warn("VibrationClassifier not trained.")
            return None
            
        # Simplified proxy features derived from the residual window
        X = np.array([[
            residual_window.channel_residuals.get("vibration_residual_mean", 0.0),
            residual_window.channel_residuals.get("vibration_residual_std", 0.0),
            residual_window.channel_residuals.get("vibration_residual_max_abs", 0.0),
            residual_window.channel_residuals.get("vibration_residual_slope", 0.0),
        ]]) 
        pred = self.clf.predict(X)
        return str(pred[0])

class TabularFaultClassifier:
    """
    Classifies tabular multi-mode faults: Injector Abnormalities, Lubrication Issues, Overheating.
    """
    def __init__(self):
        self.clf = RandomForestClassifier(n_estimators=50, random_state=42)
        self.is_trained = False
        
    def fit_dummy(self, X: np.ndarray, y: np.ndarray) -> None:
        self.clf.fit(X, y)
        self.is_trained = True

    def predict(self, residual_window: ResidualWindow) -> str | None:
        if not self.is_trained:
            warnings.warn("TabularClassifier not trained.")
            return None
            
        # Extract relevant residuals for tabular faults (mean, std, max_abs, slope for egt, oil, fuel)
        features = []
        for channel in ["egt", "oil_pressure", "fuel_flow"]:
            features.extend([
                residual_window.channel_residuals.get(f"{channel}_residual_mean", 0.0),
                residual_window.channel_residuals.get(f"{channel}_residual_std", 0.0),
                residual_window.channel_residuals.get(f"{channel}_residual_max_abs", 0.0),
                residual_window.channel_residuals.get(f"{channel}_residual_slope", 0.0),
            ])
            
        X = np.array([features]) 
        pred = self.clf.predict(X)
        return str(pred[0])

def detect_sensor_drift(residual_window: ResidualWindow) -> bool:
    """
    Detects sensor drift (synthetic scenario).
    No ML model needed; we simply check if a single channel's residual exhibits 
    sustained one-directional drift over a threshold.
    """
    egt_res_mean = residual_window.channel_residuals.get("egt_residual_mean", 0.0)
    egt_res_slope = residual_window.channel_residuals.get("egt_residual_slope", 0.0)
    # Simple threshold check for sustained drift (mock logic for the window)
    if egt_res_mean > 20.0 and abs(egt_res_slope) > 0.5:
        return True
    return False


def main():
    print("=== Fault Detection & Predictive Analytics ===")
    
    # 1. Validation Hooks
    validate_against_cwru()
    validate_against_ai4i()
    
    # 2. Train classifiers on simulator data
    print("\n--- Training Classifiers ---")
    
    reference_model = PhysicsReferenceModel()
    extractor = ResidualFeatureExtractor(reference_model)
    generator = FaultDatasetGenerator(seed=42, extractor=extractor)
    
    # Generate vibration datasets
    ds_norm = generator.generate_normal(num_runs=5, steps_per_run=20)
    ds_vib = generator.generate_fault(FaultType.ABNORMAL_VIBRATION, num_runs=5, steps_per_run=20)
    ds_misfire = generator.generate_fault(FaultType.MISFIRE, num_runs=5, steps_per_run=20)
    ds_comb = generator.generate_fault(FaultType.COMBUSTION_INSTABILITY, num_runs=5, steps_per_run=20)
    
    X_vib_list, y_vib_list = [], []
    for ds, label in [(ds_norm, "NORMAL"), (ds_vib, FaultType.ABNORMAL_VIBRATION.value), (ds_misfire, FaultType.MISFIRE.value), (ds_comb, FaultType.COMBUSTION_INSTABILITY.value)]:
        for sample in ds.samples:
            vec = sample.features
            feats = [
                vec.features.get("vibration_residual_mean", 0.0),
                vec.features.get("vibration_residual_std", 0.0),
                vec.features.get("vibration_residual_max_abs", 0.0),
                vec.features.get("vibration_residual_slope", 0.0)
            ]
            X_vib_list.append(feats)
            y_vib_list.append(label)
            
    vib_clf = VibrationFaultClassifier()
    vib_clf.fit_dummy(np.array(X_vib_list), np.array(y_vib_list))
    print("Vibration Fault Classifier trained on simulator residual features.")
    
    # Generate tabular datasets
    ds_over = generator.generate_fault(FaultType.OVERHEATING, num_runs=5, steps_per_run=20)
    ds_lube = generator.generate_fault(FaultType.LUBRICATION_FAILURE, num_runs=5, steps_per_run=20)
    
    X_tab_list, y_tab_list = [], []
    for ds, label in [(ds_norm, "NORMAL"), (ds_over, FaultType.OVERHEATING.value), (ds_lube, FaultType.LUBRICATION_FAILURE.value)]:
        for sample in ds.samples:
            vec = sample.features
            feats = []
            for channel in ["egt", "oil_pressure", "fuel_flow"]:
                feats.extend([
                    vec.features.get(f"{channel}_residual_mean", 0.0),
                    vec.features.get(f"{channel}_residual_std", 0.0),
                    vec.features.get(f"{channel}_residual_max_abs", 0.0),
                    vec.features.get(f"{channel}_residual_slope", 0.0)
                ])
            X_tab_list.append(feats)
            y_tab_list.append(label)

    tab_clf = TabularFaultClassifier()
    tab_clf.fit_dummy(np.array(X_tab_list), np.array(y_tab_list))
    print("Tabular Fault Classifier trained on simulator residual features.")
    
    # 3. Simulate consuming a ResidualWindow from the AI/ML Layer
    print("\n--- Running Fault Advisory Inference ---")
    # We pretend Script 01 emitted this window
    mock_window = ResidualWindow(
        start_time=10.0,
        end_time=15.0,
        channel_residuals={
            "egt_residual_mean": 55.0,
            "egt_residual_std": 5.0,
            "egt_residual_max_abs": 60.0,
            "egt_residual_slope": 1.5,
            "vibration_residual_mean": 0.2,
            "vibration_residual_std": 0.05,
            "vibration_residual_max_abs": 0.25,
            "vibration_residual_slope": 0.01,
            "oil_pressure_residual_mean": -5.0,
            "oil_pressure_residual_std": 1.0,
            "oil_pressure_residual_max_abs": 5.5,
            "oil_pressure_residual_slope": -0.5,
            "fuel_flow_residual_mean": 0.5,
            "fuel_flow_residual_std": 0.1,
            "fuel_flow_residual_max_abs": 0.6,
            "fuel_flow_residual_slope": 0.0
        },
        anomaly_score=0.85,
        is_anomalous=True
    )
    
    print(f"Received anomalous ResidualWindow (score: {mock_window.anomaly_score:.2f})")
    
    # Check sensor drift first
    if detect_sensor_drift(mock_window):
        print("-> Diagnosis: SENSOR_DRIFT detected (via sustained slope threshold)")
    else:
        # Route to the appropriate classifier based on the residual profile
        # For this prototype, we'll consult both and see if one finds a strong match.
        # (In reality, you'd stack them or route based on highest residual deviation)
        
        tab_pred = tab_clf.predict(mock_window)
        vib_pred = vib_clf.predict(mock_window)
        
        print(f"-> Tabular Pipeline Output: {tab_pred}")
        print(f"-> Vibration Pipeline Output (Proxy): {vib_pred}")

if __name__ == "__main__":
    main()
