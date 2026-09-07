from __future__ import annotations

import os
import warnings
import pandas as pd
import numpy as np

# Data directory paths
CMAPSS_DIR = os.environ.get("SIH_CMAPSS_DIR", "data/cmapss")
CWRU_DIR = os.environ.get("SIH_CWRU_DIR", "data/cwru")
AI4I_PATH = os.environ.get("SIH_AI4I_PATH", "data/ai4i/ai4i2020.csv")

def compute_cmapss_rul(df: pd.DataFrame) -> pd.DataFrame:
    """Computes and adds a Remaining Useful Life (RUL) column to a C-MAPSS dataframe."""
    if "unit_number" not in df.columns or "time_in_cycles" not in df.columns:
        return df
    
    # RUL is max cycles for the unit minus current cycle
    max_cycles = df.groupby("unit_number")["time_in_cycles"].transform("max")
    df["RUL"] = max_cycles - df["time_in_cycles"]
    return df

def load_cmapss(path: str = CMAPSS_DIR) -> pd.DataFrame:
    """
    Load the NASA C-MAPSS (Turbofan Engine Degradation Simulation Dataset).
    
    Source: https://ti.arc.nasa.gov/tech/dash/groups/pcoe/prognostic-data-repository/
    
    Purpose in this project: 
    Validates our RUL methodology/architecture (Quantile Regression or similar). 
    We tune our RUL model on this known-good public benchmark before re-fitting 
    it to our own simulator's degradation runs.
    """
    if os.path.isdir(path):
        path = os.path.join(path, "train_FD001.txt")
        
    if not os.path.exists(path):
        print(f"Warning: C-MAPSS data not found at {path}.")
        return pd.DataFrame()
        
    columns = ["unit_number", "time_in_cycles", "op_setting_1", "op_setting_2", "op_setting_3"] + [f"sensor_{i}" for i in range(1, 22)]
    try:
        df = pd.read_csv(path, sep=r"\s+", header=None, names=columns, engine="python")
        df = df.dropna(axis=1, how="all") # Drop fully-empty trailing columns
        return df
    except Exception as e:
        print(f"Error loading C-MAPSS data: {e}")
        return pd.DataFrame()


def load_cwru(path: str = CWRU_DIR) -> tuple[pd.DataFrame, dict[str, str | int | float]]:
    """
    Load the CWRU Bearing Dataset (Case Western Reserve University).
    
    Source: https://engineering.case.edu/bearingdatacenter
    
    Purpose in this project:
    Validates the high-frequency vibration fault signatures (FFT/waveform pipeline).
    Our simulator currently only emits a 1Hz scalar proxy for vibration, so this 
    loader acts as a reference for how true vibration diagnosis would be validated 
    before application to a high-rate telemetry stream.
    
    Returns:
        A tuple of (DataFrame containing time series, metadata dictionary).
    """
    if os.path.isdir(path):
        # Default to a specific file if directory is provided, or return empty if we can't guess
        # Let's try to find an .npz file or .mat file
        files = os.listdir(path) if os.path.exists(path) else []
        npz_files = [f for f in files if f.endswith('.npz')]
        mat_files = [f for f in files if f.endswith('.mat')]
        
        if npz_files:
            path = os.path.join(path, npz_files[0])
        elif mat_files:
            path = os.path.join(path, mat_files[0])
        else:
            print(f"Warning: No .npz or .mat files found in {path}.")
            return pd.DataFrame(), {}
            
    if not os.path.exists(path):
        print(f"Warning: CWRU data not found at {path}.")
        return pd.DataFrame(), {}

    metadata = {
        "fault_type": os.path.basename(path).split(".")[0],
    }

    try:
        if path.endswith(".npz"):
            data = np.load(path)
            # Find a valid array key
            valid_keys = [k for k in data.files if data[k].ndim == 1 or (data[k].ndim == 2 and data[k].shape[1] == 1)]
            if not valid_keys:
                return pd.DataFrame(), metadata
                
            key = valid_keys[0]
            # Simple assumption: 12kHz or 48kHz
            metadata["sample_rate_hz"] = 12000
            df = pd.DataFrame({key: data[key].flatten()})
            return df, metadata
            
        elif path.endswith(".mat"):
            import scipy.io
            data = scipy.io.loadmat(path)
            
            # Find vibration arrays
            time_series_keys = [k for k in data.keys() if k.endswith("_DE_time") or k.endswith("_FE_time") or k.endswith("_BA_time")]
            rpm_keys = [k for k in data.keys() if k.endswith("RPM")]
            
            if rpm_keys:
                metadata["rpm"] = float(data[rpm_keys[0]].item())
                
            metadata["sample_rate_hz"] = 12000
                
            if not time_series_keys:
                return pd.DataFrame(), metadata
                
            df_dict = {k: data[k].flatten() for k in time_series_keys}
            return pd.DataFrame(df_dict), metadata
            
        else:
            print(f"Unsupported file format for CWRU data: {path}")
            return pd.DataFrame(), metadata
            
    except Exception as e:
        print(f"Error loading CWRU data: {e}")
        return pd.DataFrame(), {}


def load_ai4i(path: str = AI4I_PATH) -> pd.DataFrame:
    """
    Load the AI4I 2020 Predictive Maintenance Dataset.
    
    Source: UCI Machine Learning Repository (https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset)
    
    Purpose in this project:
    Validates the tabular multi-mode fault classification approach (Random Forest/LightGBM).
    We map its failure modes (Tool Wear, Heat Dissipation Failure, etc.) to our closest 
    equivalent categories (e.g., Lubrication Issues, Overheating).
    """
    if not os.path.exists(path):
        print(f"Warning: AI4I data not found at {path}.")
        return pd.DataFrame()
        
    try:
        df = pd.read_csv(path)
        
        # Rename columns to snake_case
        rename_map = {
            "UDI": "udi",
            "Product ID": "product_id",
            "Type": "type",
            "Air temperature [K]": "air_temperature_k",
            "Process temperature [K]": "process_temperature_k",
            "Rotational speed [rpm]": "rotational_speed_rpm",
            "Torque [Nm]": "torque_nm",
            "Tool wear [min]": "tool_wear_min",
            "Machine failure": "machine_failure"
        }
        df = df.rename(columns=rename_map)
        
        # Add explicit mapping dict
        # AI4I_TO_FAULTTYPE = {
        #     "HDF": "OVERHEATING",           # Heat Dissipation Failure
        #     "PWF": "SENSOR_FAILURE",        # Power Failure -> closest electrical proxy
        #     "OSF": "LUBRICATION_FAILURE",   # Overstrain -> closest mechanical-load proxy
        #     "TWF": "COMBUSTION_INSTABILITY",# Tool Wear -> closest progressive-wear proxy
        #     "RNF": None,                    # Random failure has no deterministic cause
        # }
        
        return df
    except Exception as e:
        print(f"Error loading AI4I data: {e}")
        return pd.DataFrame()
