import os
import pandas as pd
import subprocess
from itertools import product
from tqdm import tqdm  # ✅ Import progress bar

# Parameters to sweep
kl_thresholds = [0.5, 1.0, 1.5, 2.0]
error_history_lengths = [5, 10, 20, 30]

os.environ["SIM_START"] = "2016-05-02 23:00:00"
os.environ["SIM_END"] = "2016-05-06 23:00:00"

# Create output directory for logs
os.makedirs("results/sweep_logs", exist_ok=True)

# Run simulations for each parameter pair with progress bar
results = []
sweep_combinations = list(product(kl_thresholds, error_history_lengths))

for kl, history in tqdm(sweep_combinations, desc="Sweeping parameters", unit="config"):
    # Print current run
    print(f"\nRunning simulation for KL={kl}, history={history}")

    # Define environment variables
    os.environ["KL_THRESHOLD"] = str(kl)
    os.environ["ERROR_HISTORY"] = str(history)

    # Run the simulation
    subprocess.run(["python", "scripts/run_simulation.py"], check=True)

    # Load transmission log
    tx_log = pd.read_csv("results/transmission_log_combined.csv")
    tx_log = tx_log[tx_log["sensor_type"] == "universal"]

    # Metrics
    transmissions = len(tx_log)
    total_energy_j = tx_log["energy_used_mJ"].sum() / 1000
    avg_sampling_rate = tx_log["sampling_rate"].mean()

    # Hotspot recovery
    exp_log = pd.read_csv("results/experiment_log_combined.csv")
    exp_log = exp_log[exp_log["sensor_type"] == "universal"]
    exp_log["key"] = exp_log["sensor_id"].astype(str) + "_" + exp_log["datetime"].astype(str)
    tx_log["key"] = tx_log["sensor_id"].astype(str) + "_" + tx_log["timestamp"].astype(str)
    exp_log["transmitted"] = exp_log["key"].isin(tx_log["key"])

    hotspots = exp_log[exp_log["hotspot"] == 1]
    hotspot_transmitted = hotspots["transmitted"].sum()
    hotspot_total = len(hotspots)
    hotspot_rate = hotspot_transmitted / hotspot_total if hotspot_total > 0 else 0

    results.append({
        "kl_threshold": kl,
        "error_history": history,
        "transmissions": transmissions,
        "energy_j": total_energy_j,
        "avg_sampling_rate": avg_sampling_rate,
        "hotspot_recovery_rate": hotspot_rate
    })

# Save results
sweep_df = pd.DataFrame(results)
sweep_df.to_csv("results/sweep_logs/summary_metrics.csv", index=False)
print("\nSweep completed and saved to results/sweep_logs/summary_metrics.csv")
