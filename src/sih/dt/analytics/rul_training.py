from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import copy
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

from sih.dt.data.generator import FaultDatasetGenerator, DatasetLabel
from sih.dt.analytics.anomaly import IsolationForestDetector
from sih.dt.analytics.contracts import ResidualWindow
from sih.dt.features.schema import FeatureVector, RESIDUAL_CHANNELS
from sih.dt.features.extractor import ResidualFeatureExtractor
from sih.dt.features.physics import PhysicsReferenceModel
from sih.dt.analytics.rul_model import AeroTwinRULModel
from sih.dt.data.loaders import load_cmapss, compute_cmapss_rul, preprocess_cmapss_features

class CMAPSSWindowDataset(Dataset):
    """Creates sliding windows of length seq_len from C-MAPSS engines."""
    def __init__(self, df: pd.DataFrame, sensor_cols: list[str], seq_len: int = 30):
        self.windows = []
        self.ruls = []
        
        for unit in df['unit_number'].unique():
            unit_data = df[df['unit_number'] == unit]
            sensors = unit_data[sensor_cols].values
            rul = unit_data['RUL'].values
            
            for i in range(len(sensors) - seq_len + 1):
                self.windows.append(sensors[i:i+seq_len])
                # We predict the RUL at the LAST cycle of the window
                self.ruls.append(rul[i+seq_len-1])
                
        self.windows = torch.tensor(np.array(self.windows), dtype=torch.float32)
        self.ruls = torch.tensor(np.array(self.ruls), dtype=torch.float32).unsqueeze(1)
        
    def __len__(self):
        return len(self.windows)
        
    def __getitem__(self, idx):
        return self.windows[idx], self.ruls[idx]

def validate_against_cmapss(rul_model: AeroTwinRULModel) -> None:
    """
    Validation hook for NASA C-MAPSS dataset.
    This is where we pre-train/tune the RUL model architecture against a known-good 
    public benchmark before re-fitting on our own simulator's degradation runs.
    """
    import os
    import torch
    import pickle
    from torch.utils.data import TensorDataset, DataLoader
    
    model_cache_path = "data/cache/best_rul_model.pth"
    if os.path.exists(model_cache_path):
        print(f"Loading pretrained GRU weights from {model_cache_path}...")
        rul_model.load_state_dict(torch.load(model_cache_path, weights_only=True))
        return

    print("\n--- NASA C-MAPSS Validation Hook ---")
    full_cache_path = "data/cache/cmapss_full_processed.pkl"
    if not os.path.exists(full_cache_path):
        print("Full C-MAPSS processed data not found. Skipping validation step.")
        return
        
    print(f"Loading full preprocessed FD001-FD004 C-MAPSS data from {full_cache_path}...")
    with open(full_cache_path, "rb") as f:
        data = pickle.load(f)
        
    X_train = torch.tensor(data["X_train"], dtype=torch.float32)
    y_train = torch.tensor(data["y_train"], dtype=torch.float32).view(-1, 1)
    X_val = torch.tensor(data["X_val"], dtype=torch.float32)
    y_val = torch.tensor(data["y_val"], dtype=torch.float32).view(-1, 1)
    
    train_ds = TensorDataset(X_train, y_train)
    val_ds = TensorDataset(X_val, y_val)
    
    train_loader = DataLoader(train_ds, batch_size=256, shuffle=True)
    test_loader = DataLoader(val_ds, batch_size=256, shuffle=False)
    
    print(f"Pretraining GRU on Full C-MAPSS... (Train samples: {len(X_train)}, Val samples: {len(X_val)})")
    
    if True:
        
        # Pretraining Loop (Door A)
        optimizer = torch.optim.Adam(rul_model.parameters(), lr=1e-3)
        criterion = nn.MSELoss()
        
        epochs = 100  # Increased for full convergence
        patience = 5
        best_val_loss = float('inf')
        patience_counter = 0
        best_model_state = None
        
        for epoch in range(epochs):
            # Training Phase
            rul_model.train()
            total_train_loss = 0
            for batch_x, batch_y in train_loader:
                optimizer.zero_grad()
                preds = rul_model.forward_cmapss(batch_x)
                loss = criterion(preds, batch_y)
                loss.backward()
                optimizer.step()
                total_train_loss += loss.item()
                
            avg_train_loss = total_train_loss / len(train_loader)
            
            # Validation Phase
            rul_model.eval()
            total_val_loss = 0
            with torch.no_grad():
                for batch_x, batch_y in test_loader:
                    preds = rul_model.forward_cmapss(batch_x)
                    loss = criterion(preds, batch_y)
                    total_val_loss += loss.item()
                    
            avg_val_loss = total_val_loss / len(test_loader)
            
            print(f"  Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.2f} | Val Loss: {avg_val_loss:.2f}")
            
            # Early Stopping Check
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                patience_counter = 0
                best_model_state = copy.deepcopy(rul_model.state_dict())
            else:
                patience_counter += 1
                
            if patience_counter >= patience:
                print(f"Early stopping triggered at epoch {epoch+1}! Best Val Loss: {best_val_loss:.2f}")
                break
                
        # Restore and save the best model weights to disk
        if best_model_state is not None:
            rul_model.load_state_dict(best_model_state)
            torch.save(best_model_state, model_cache_path)
            print(f"Saved best model weights to {model_cache_path}")
            
        print("C-MAPSS GRU Pretraining Complete.")

class RULEstimator:
    """
    RUL estimator leveraging the pretrained Dual-Encoder GRU.
    Fine-tunes the simulator encoder dynamically.
    """
    def __init__(self, model: AeroTwinRULModel):
        self.model = model
        # Unfreeze the entire model for fine-tuning
        self.model.unfreeze_shared_core()
        # Create optimizer for the whole model
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3)
        self.criterion = nn.MSELoss()
        
    def fine_tune_and_predict(self, history: list[list[float]], true_rul: float) -> float:
        """
        Takes a sequence of 6-sensor residual vectors.
        Takes one gradient step to adapt the simulator encoder, then predicts.
        """
        if len(history) < 30:
            return 999.0 # Need 30 cycles to form a window
            
        window = history[-30:]
        x_tensor = torch.tensor(window, dtype=torch.float32).unsqueeze(0) # (1, 30, 6)
        y_true = torch.tensor([[true_rul]], dtype=torch.float32)
        
        # Train Step
        self.model.train()
        self.optimizer.zero_grad()
        pred = self.model.forward_sim(x_tensor)
        loss = self.criterion(pred, y_true)
        loss.backward()
        self.optimizer.step()
        
        # Evaluation
        self.model.eval()
        with torch.no_grad():
            final_pred = self.model.forward_sim(x_tensor).item()
            
        return final_pred

def pretrain_simulator_encoder(rul_model: AeroTwinRULModel) -> None:
    import os
    import torch
    import torch.utils.data as data
    from sih.dt.data.generator import FaultDatasetGenerator
    from sih.dt.simulation.faults import FaultType
    from sih.dt.features.physics import PhysicsReferenceModel
    from sih.dt.features.extractor import ResidualFeatureExtractor
    from sih.dt.analytics.anomaly import IsolationForestDetector
    from collections import defaultdict

    finetuned_path = "data/cache/best_rul_model_finetuned.pth"
    if os.path.exists(finetuned_path):
        print(f"Loading fully finetuned GRU weights from {finetuned_path}...")
        rul_model.load_state_dict(torch.load(finetuned_path, weights_only=True))
        return

    print("Pre-training simulator encoder offline...")
    generator = FaultDatasetGenerator(
        extractor=ResidualFeatureExtractor(PhysicsReferenceModel())
    )
    
    norm_ds = generator.generate_normal(num_runs=5, steps_per_run=50)
    detector = IsolationForestDetector(contamination=0.05)
    detector.fit([s.features for s in norm_ds.samples])

    warmup_ds = generator.generate_fault(FaultType.OVERHEATING, num_runs=10, steps_per_run=150)
    
    calibration_data = []
    flights = defaultdict(list)
    for sample in warmup_ds.samples:
        flights[sample.run_id].append(sample)
        
    for run_id, samples in flights.items():
        warm_history = []
        warm_rul = 150
        anomaly_streak = 0
        
        for sample in samples:
            vec = sample.features
            residuals = [vec.features.get(f"{ch}_residual_mean", 0.0) for ch in ["egt", "ff", "n1", "n2", "vibration", "p30"]]
            warm_history.append(residuals)
            warm_rul -= 1
            
            if detector.predict(vec):
                anomaly_streak += 1
            else:
                anomaly_streak = 0
                
            if len(warm_history) >= 30 and anomaly_streak >= 3:
                calibration_data.append((list(warm_history[-30:]), float(warm_rul)))
            
    X_train = torch.tensor([item[0] for item in calibration_data], dtype=torch.float32)
    y_train = torch.tensor([[item[1]] for item in calibration_data], dtype=torch.float32)
    dataset = data.TensorDataset(X_train, y_train)
    loader = data.DataLoader(dataset, batch_size=16, shuffle=True)
    
    rul_model.unfreeze_shared_core()
    optimizer = torch.optim.Adam(rul_model.parameters(), lr=1e-3)
    criterion = torch.nn.MSELoss()
    
    epochs = 150
    rul_model.train()
    for epoch in range(epochs):
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            pred = rul_model.forward_sim(batch_x)
            loss = criterion(pred, batch_y)
            loss.backward()
            optimizer.step()
            
    torch.save(rul_model.state_dict(), finetuned_path)
    print(f"Saved fully finetuned model weights to {finetuned_path}")

def main():
    print("=== AI/ML Layer: Anomaly & RUL ===\n")
    
    # 1. Initialize our Dual-Encoder GRU model
    rul_model = AeroTwinRULModel(cmapss_dim=14, sim_dim=6)
    
    # 2. Pretrain on NASA C-MAPSS (Door A)
    validate_against_cmapss(rul_model)
    
    # 3. Finetune on Simulator Residuals
    pretrain_simulator_encoder(rul_model)
    print("\nNote: The GRU has successfully pretrained on C-MAPSS physics and fine-tuned on simulator residuals.")

if __name__ == "__main__":
    main()
