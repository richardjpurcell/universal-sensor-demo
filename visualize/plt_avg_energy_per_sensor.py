import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Plot settings
sns.set_context("talk")
plt.rcParams.update({
    "axes.titlesize": 18,
    "axes.labelsize": 16,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "legend.fontsize": 14,
    "figure.titlesize": 18
})

os.makedirs("results/figures", exist_ok=True)

# Load logs
tx_df = pd.read_csv("results/transmission_log_combined.csv")
sensor_df = pd.read_csv("results/sensor_deployment.csv")

# Add sensor_id based on row number
# Add sensor_id to sensor_df
sensor_df["sensor_id"] = sensor_df.index

# Create a matching key for merge
sensor_df["sensor_key"] = (
    sensor_df["x"].round(3).astype(str) + "_" +
    sensor_df["y"].round(3).astype(str) + "_" +
    sensor_df["sensor_type"]
)
tx_df["sensor_key"] = (
    tx_df["x"].round(3).astype(str) + "_" +
    tx_df["y"].round(3).astype(str) + "_" +
    tx_df["sensor_type"]
)

# Merge sensor_id and coordinates
tx_df = tx_df.merge(sensor_df[["sensor_key", "sensor_id"]], on="sensor_key", how="left")

# Merge distance into transmission log
sensor_coords = sensor_df[["sensor_id", "sensor_type", "x", "y"]]
tx_df = tx_df.merge(sensor_coords, on=["x", "y", "sensor_type"], how="left")

# Calculate distance from base station
# Define base station as center of deployed sensor region
base_x = sensor_df["x"].mean()
base_y = sensor_df["y"].mean()

tx_df["distance_km"] = np.sqrt((tx_df["x"] - base_x)**2 + (tx_df["y"] - base_y)**2) / 1000

# Aggregate metrics per sensor
agg = tx_df.groupby(["sensor_id", "sensor_type", "distance_km"]).agg({
    "energy_used_mJ": "mean",
    "data_sent_bytes": "mean"
}).reset_index()

# Rename for clarity
agg.rename(columns={
    "energy_used_mJ": "Avg Energy per Tx (mJ)",
    "data_sent_bytes": "Avg Tx Size (bytes)"
}, inplace=True)

# ---------------------------
# OUTLIER FILTERING (IQR)
# ---------------------------
def remove_outliers_iqr(df, column):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

# Apply to both energy and tx size
agg = remove_outliers_iqr(agg, "Avg Energy per Tx (mJ)")
agg = remove_outliers_iqr(agg, "Avg Tx Size (bytes)")


# Plot 1: Average Energy per Transmission
plt.figure(figsize=(10, 6))
sns.scatterplot(data=agg, x="distance_km", y="Avg Energy per Tx (mJ)", hue="sensor_type", alpha=0.7)

# Per-sensor-type means
for sensor_type, color in zip(["typical", "universal"], ["blue", "green"]):
    mean_val = agg[agg["sensor_type"] == sensor_type]["Avg Energy per Tx (mJ)"].mean()
    plt.axhline(mean_val, color=color, linestyle=':', label=f"{sensor_type.capitalize()} Mean")


plt.title("Avg Energy per Transmission vs Distance")
plt.xlabel("Distance from Base Station (km)")
plt.ylabel("Avg Energy per Tx (mJ)")
plt.legend(title="Sensor Type", loc="lower right")
plt.tight_layout()
plt.savefig("results/figures/avg_energy_vs_distance.png", dpi=300)
plt.close()

# Plot 2: Average Transmission Size
plt.figure(figsize=(10, 6))
sns.scatterplot(data=agg, x="distance_km", y="Avg Tx Size (bytes)", hue="sensor_type", alpha=0.6, s=15)

# Per-sensor-type means
for sensor_type, color in zip(["typical", "universal"], ["blue", "green"]):
    mean_val = agg[agg["sensor_type"] == sensor_type]["Avg Tx Size (bytes)"].mean()
    plt.axhline(mean_val, color=color, linestyle=':', label=f"{sensor_type.capitalize()} Mean")

plt.title("Avg Transmission Size vs Distance")
plt.xlabel("Distance from Base Station (km)")
plt.ylabel("Avg Tx Size (bytes)")
plt.legend(title="Sensor Type", loc="center left", bbox_to_anchor=(1, 0.5))
#plt.legend(title="Sensor Type")
plt.tight_layout()
plt.savefig("results/figures/avg_txsize_vs_distance.png", dpi=300)
plt.close()

print("[Saved] results/figures/avg_energy_vs_distance.png")
print("[Saved] results/figures/avg_txsize_vs_distance.png")
