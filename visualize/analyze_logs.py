import pandas as pd
import os

# Paths
TX_PATH = "results/transmission_log_combined_FINAL.csv"
EXP_PATH = "results/experiment_log_combined_FINAL.csv"
OUTPUT_PATH = "results/tables/final_transmission_metrics.csv"

os.makedirs("results/tables", exist_ok=True)

# Load logs
tx = pd.read_csv(TX_PATH, parse_dates=["timestamp"])
exp = pd.read_csv(EXP_PATH, parse_dates=["datetime"])

# Prepare result dictionary
metrics = {
    "Metric": [
        "Transmissions",
        "Total Data (KB)",
        "Total Energy (J)",
        "Avg Energy / Tx (mJ)",
        "Avg Tx Size (bytes)",
        "Avg Sampling Rate"
    ],
    "Typical": [],
    "Universal": []
}

# Define helper
def compute_metrics(subset):
    transmissions = len(subset)
    total_data_kb = subset["data_sent_bytes"].sum() / 1024
    total_energy_j = subset["energy_used_mJ"].sum() / 1000
    avg_energy_mJ = subset["energy_used_mJ"].mean()
    avg_tx_size = subset["data_sent_bytes"].mean()
    return transmissions, total_data_kb, total_energy_j, avg_energy_mJ, avg_tx_size

# Compute for each type
for label in ["typical", "universal"]:
    tx_sub = tx[tx["sensor_type"] == label]
    transmissions, data_kb, energy_j, avg_energy, avg_size = compute_metrics(tx_sub)

    # Sampling rate (only for Universal)
    if label == "universal":
        avg_sampling_rate = tx_sub["sampling_rate"].mean()
    else:
        avg_sampling_rate = None

    metrics[label.capitalize()] = [
        f"{transmissions:,}",
        f"{data_kb:,.0f}",
        f"{energy_j:,.0f}",
        f"{avg_energy:.2f}",
        f"{avg_size:,.0f}",
        f"{avg_sampling_rate:.3f}" if avg_sampling_rate is not None else "—"
    ]

# Save
df = pd.DataFrame(metrics)
df.to_csv(OUTPUT_PATH, index=False)
print(df.to_string(index=False))
print(f"[Saved] {OUTPUT_PATH}")
