from __future__ import annotations

import os
import zipfile
import warnings
import pickle
import pandas as pd
import numpy as np

# Data directory paths
CMAPSS_DIR = os.environ.get("SIH_CMAPSS_DIR", r"C:\Users\mohit\Documents\AeroTwin_datasets\6.+Turbofan+Engine+Degradation+Simulation+Data+Set\6. Turbofan Engine Degradation Simulation Data Set\CMAPSSData.zip")
CWRU_DIR = os.environ.get("SIH_CWRU_DIR", r"C:\Users\mohit\Documents\AeroTwin_datasets\srigas CWRU_Bearing_NumPy main Data-1797 RPM")
AI4I_PATH = os.environ.get("SIH_AI4I_PATH", r"C:\Users\mohit\Documents\AeroTwin_datasets\ai4i+2020+predictive+maintenance+dataset\ai4i2020.csv")

# Cache directory
CACHE_DIR = "data/cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def compute_cmapss_rul(df: pd.DataFrame) -> pd.DataFrame:
    """Computes and adds a Remaining Useful Life (RUL) column to a C-MAPSS dataframe, capped at 125."""
    if "unit_number" not in df.columns or "time_in_cycles" not in df.columns:
        return df
    
    # RUL is max cycles for the unit minus current cycle
    max_cycles = df.groupby("unit_number")["time_in_cycles"].transform("max")
    df["RUL"] = max_cycles - df["time_in_cycles"]
    df["RUL"] = df["RUL"].clip(upper=125)
    return df

def preprocess_cmapss_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies a rolling mean of 5 cycles per engine, strictly to the sensor columns.
    Then computes pseudo-residuals by taking the first 10 cycles as the healthy baseline 
    and subtracting it from the entire trajectory, bringing it into the residual domain.
    """
    sensor_cols = [c for c in df.columns if c.startswith("sensor_")]
    
    # 1. Light Smoothing
    df[sensor_cols] = df.groupby("unit_number")[sensor_cols].transform(lambda x: x.rolling(window=5, min_periods=1).mean())
    
    # 2. Residual Alignment (Subtract baseline)
    # Get the mean of the first 10 cycles for each engine
    baselines = df[df["time_in_cycles"] <= 10].groupby("unit_number")[sensor_cols].mean()
    
    # Subtract the baseline from the respective engines
    for unit_num, baseline_vals in baselines.iterrows():
        mask = df["unit_number"] == unit_num
        df.loc[mask, sensor_cols] = df.loc[mask, sensor_cols] - baseline_vals
        
    return df

def load_cmapss(path: str = CMAPSS_DIR) -> pd.DataFrame:
    """
    Load the NASA C-MAPSS (Turbofan Engine Degradation Simulation Dataset).
    Strictly loads FD001. Uses cached pickle if available.
    """
    cache_path = os.path.join(CACHE_DIR, "cmapss_fd001.pkl")
    if os.path.exists(cache_path):
        print("Loading C-MAPSS from cache...")
        return pd.read_pickle(cache_path)
        
    try:
        if path.endswith(".zip"):
            with zipfile.ZipFile(path, 'r') as z:
                with z.open("train_FD001.txt") as f:
                    df = pd.read_csv(f, sep=r"\s+", header=None, engine="python")
        elif os.path.isdir(path):
            file_path = os.path.join(path, "train_FD001.txt")
            df = pd.read_csv(file_path, sep=r"\s+", header=None, engine="python")
        else:
            df = pd.read_csv(path, sep=r"\s+", header=None, engine="python")
            
        columns = ["unit_number", "time_in_cycles", "op_setting_1", "op_setting_2", "op_setting_3"] + [f"sensor_{i}" for i in range(1, 22)]
        df.columns = columns
        
        # Drop constant sensors
        constant_sensors = ["sensor_1", "sensor_5", "sensor_6", "sensor_10", "sensor_16", "sensor_18", "sensor_19"]
        df = df.drop(columns=constant_sensors, errors="ignore")
        
        # Drop any fully-empty trailing columns
        df = df.dropna(axis=1, how="all")
        
        # Save to cache
        df.to_pickle(cache_path)
        return df
    except Exception as e:
        print(f"Error loading C-MAPSS data: {e}")
        return pd.DataFrame()


def load_cwru(path: str = CWRU_DIR) -> list[tuple[pd.DataFrame, dict[str, str | int | float]]]:
    """
    Load the CWRU Bearing Dataset (Case Western Reserve University).
    Returns a list of (DataFrame, metadata) tuples for all valid files in the directory.
    Uses cached pickle if available.
    """
    cache_path = os.path.join(CACHE_DIR, "cwru_processed.pkl")
    if os.path.exists(cache_path):
        print("Loading CWRU from cache...")
        with open(cache_path, "rb") as f:
            return pickle.load(f)
            
    results = []
    
    if os.path.isfile(path):
        files_to_load = [path]
        base_dir = os.path.dirname(path)
    elif os.path.isdir(path):
        files = os.listdir(path) if os.path.exists(path) else []
        files_to_load = [os.path.join(path, f) for f in files if f.endswith('.npz') or f.endswith('.mat')]
    else:
        print(f"Warning: CWRU data not found at {path}.")
        return results
        
    for file_path in files_to_load:
        metadata = {
            "fault_type": os.path.basename(file_path).split(".")[0],
            "file_name": os.path.basename(file_path)
        }


        try:
            if file_path.endswith(".npz"):
                data = np.load(file_path)
                valid_keys = [k for k in data.files if data[k].ndim == 1 or (data[k].ndim == 2 and data[k].shape[1] == 1)]
                if not valid_keys:
                    continue
                    
                key = valid_keys[0]
                metadata["sample_rate_hz"] = 12000
                arr = data[key].flatten()
                
                if arr.std() > 0:
                    arr = (arr - arr.mean()) / arr.std()
                
                df = pd.DataFrame({key: arr})
                results.append((df, metadata))
                
            elif file_path.endswith(".mat"):
                import scipy.io
                data = scipy.io.loadmat(file_path)
                
                time_series_keys = [k for k in data.keys() if k.endswith("_DE_time") or k.endswith("_FE_time") or k.endswith("_BA_time")]
                rpm_keys = [k for k in data.keys() if k.endswith("RPM")]
                
                if rpm_keys:
                    metadata["rpm"] = float(data[rpm_keys[0]].item())
                    
                metadata["sample_rate_hz"] = 12000
                    
                if not time_series_keys:
                    continue
                    
                df_dict = {}
                for k in time_series_keys:
                    arr = data[k].flatten()
                    if arr.std() > 0:
                        arr = (arr - arr.mean()) / arr.std()
                    df_dict[k] = arr
                    
                results.append((pd.DataFrame(df_dict), metadata))
                
        except Exception as e:
            print(f"Error loading CWRU file {file_path}: {e}")
            
    if results:
        with open(cache_path, "wb") as f:
            pickle.dump(results, f)
            
    return results


def load_ai4i(path: str = AI4I_PATH) -> pd.DataFrame:
    """
    Load the AI4I 2020 Predictive Maintenance Dataset.
    Uses cached pickle if available.
    """
    cache_path = os.path.join(CACHE_DIR, "ai4i2020.pkl")
    if os.path.exists(cache_path):
        print("Loading AI4I from cache...")
        return pd.read_pickle(cache_path)
        
    if os.path.isdir(path):
        path = os.path.join(path, "ai4i2020.csv")
        
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
        
        # Drop ID columns
        df = df.drop(columns=["udi", "product_id"], errors="ignore")
        
        # Encode Type column
        df = pd.get_dummies(df, columns=["type"], drop_first=False)
        
        df.to_pickle(cache_path)
        return df
    except Exception as e:
        print(f"Error loading AI4I data: {e}")
        return pd.DataFrame()
