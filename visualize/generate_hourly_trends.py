import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Ensure output directory exists
os.makedirs("results/figures", exist_ok=True)

# Load experiment and transmission logs
exp_log = pd.read_csv("results/experiment_log_combined.csv", parse_dates=["datetime"])
tx_log = pd.read_csv("results/transmission_log_combined.csv", parse_dates=["timestamp"])

# Filter for universal sensors only
exp_log = exp_log[exp_log["sensor_type"] == "universal"]
tx_log = tx_log[tx_log["sensor_type"] == "universal"]

# Create a unique key for matching
exp_log["key"] = exp_log["sensor_id"].astype(str) + "_" + exp_log["datetime"].astype(str)
tx_log["key"] = tx_log["sensor_id"].astype(str) + "_" + tx_log["timestamp"].astype(str)

# Mark whether a record was transmitted
exp_log["transmitted"] = exp_log["key"].isin(tx_log["key"])

# Extract hour for grouping
exp_log["hour"] = exp_log["datetime"].dt.floor("H")

# Plot hourly trends for each variable
# Plot hourly trends for each variable
variables = ["temperature", "wind_speed", "relative_humidity"]

titles = {
    "temperature": "Temperature Trend Over Time",
    "wind_speed": "Wind Speed Trend Over Time",
    "relative_humidity": "Relative Humidity Trend Over Time"
}

ylabels = {
    "temperature": "Temperature (°C)",
    "wind_speed": "Wind Speed (m/s)",
    "relative_humidity": "Relative Humidity (%)"
}

filenames = {
    "temperature": "trend_temperature.png",
    "wind_speed": "trend_wind_speed.png",
    "relative_humidity": "trend_relative_humidity.png"
}

for var in variables:
    plt.figure(figsize=(10, 5))

    # Group by hour and transmission status
    grouped = exp_log.groupby(["hour", "transmitted"])[var].mean().reset_index()

    # Plot solid for transmitted, dashed for not transmitted
    for status, style in zip([True, False], ["-", "--"]):
        subset = grouped[grouped["transmitted"] == status]
        label = "Transmitted" if status else "Retained Only"
        plt.plot(subset["hour"], subset[var], linestyle=style, label=label, linewidth=2)

    plt.title(titles[var], fontsize=16)           # New plot title
    plt.xlabel("Time (Hour)", fontsize=14)
    plt.ylabel(ylabels[var], fontsize=14)         # New Y-axis label
    plt.xticks(rotation=45, fontsize=12)
    plt.yticks(fontsize=12)
    plt.legend(fontsize=12)
    plt.tight_layout()
    plt.savefig(f"results/figures/{filenames[var]}", dpi=300)
    plt.close()

