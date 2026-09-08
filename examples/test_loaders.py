import os
from data_loaders import load_cmapss, load_cwru, load_ai4i, compute_cmapss_rul

def main():
    print("Testing CMAPSS Loader:")
    df_cmapss = load_cmapss()
    if not df_cmapss.empty:
        df_cmapss = compute_cmapss_rul(df_cmapss)
        print(f"Loaded CMAPSS: shape {df_cmapss.shape}")
        print(df_cmapss.head(2))
    else:
        print("CMAPSS data not found or empty.")

    print("\nTesting CWRU Loader:")
    cwru_results = load_cwru()
    if cwru_results:
        print(f"Loaded {len(cwru_results)} CWRU files.")
        df_cwru, meta_cwru = cwru_results[0]
        print(f"First CWRU file shape: {df_cwru.shape}")
        print(f"Metadata: {meta_cwru}")
        print(df_cwru.head(2))
    else:
        print("CWRU data not found or empty.")

    print("\nTesting AI4I Loader:")
    df_ai4i = load_ai4i()
    if not df_ai4i.empty:
        print(f"Loaded AI4I: shape {df_ai4i.shape}")
        print(df_ai4i.head(2))
    else:
        print("AI4I data not found or empty.")

if __name__ == "__main__":
    main()
