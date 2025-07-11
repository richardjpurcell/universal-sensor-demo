import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr
import os

# CONFIG
sns.set_context("talk")  # Large font sizes
plt.rcParams.update({
    "axes.titlesize": 18,
    "axes.labelsize": 16,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "legend.fontsize": 14,
    "figure.titlesize": 18
})

os.makedirs("results/figures", exist_ok=True)
os.makedirs("results/tables", exist_ok=True)

# Load logs
exp = pd.read_csv("results/experiment_log_combined.csv", parse_dates=["datetime"])
tx = pd.read_csv("results/transmission_log_combined.csv", parse_dates=["timestamp"])

# Filter for universal sensors only
exp = exp[exp["sensor_type"] == "universal"]
tx = tx[tx["sensor_type"] == "universal"]

# Merge key for alignment
exp["key"] = exp["sensor_id"].astype(str) + "_" + exp["datetime"].astype(str)
tx["key"] = tx["sensor_id"].astype(str) + "_" + tx["timestamp"].astype(str)
exp["transmitted"] = exp["key"].isin(tx["key"])

# Descriptive Stats
desc = exp.groupby("transmitted")[["temperature", "wind_speed", "relative_humidity"]].agg(["mean", "median", "std", "min", "max"])
desc.columns = ['_'.join(col) for col in desc.columns]
desc.to_csv("results/tables/descriptive_stats.csv")

# 95% Confidence Intervals
def ci95(series):
    n = len(series)
    if n == 0:
        return np.nan, np.nan
    mean = series.mean()
    margin = 1.96 * series.std(ddof=1) / np.sqrt(n)
    return mean - margin, mean + margin

ci_data = []
for var in ["temperature", "wind_speed", "relative_humidity"]:
    for label, group in exp.groupby("transmitted"):
        lower, upper = ci95(group[var])
        ci_data.append({
            "variable": var,
            "transmitted": label,
            "ci_lower": lower,
            "ci_upper": upper
        })

ci_df = pd.DataFrame(ci_data)
ci_df.to_csv("results/tables/ci95_stats.csv", index=False)

# Pearson correlation (transmitted only)
tx_exp = exp[exp["transmitted"]]
corr = tx_exp[["temperature", "wind_speed", "relative_humidity"]].corr(method="pearson")
corr.to_csv("results/tables/pearson_correlation.csv")

# Add human-readable label
exp["transmit_label"] = exp["transmitted"].map({True: "Transmitted", False: "Retained Only"})

# KDE plots
for var in ["temperature", "wind_speed", "relative_humidity"]:
    plt.figure(figsize=(10, 6))
    for label, color in zip(["Transmitted", "Retained Only"], ["blue", "orange"]):
        subset = exp[exp["transmit_label"] == label]
        if not subset.empty:
            sns.kdeplot(
                data=subset,
                x=var,
                fill=True,
                common_norm=False,
                alpha=0.5,
                label=label,
                color=color
            )
    plt.title(f"KDE of {var.replace('_', ' ').title()} (Transmitted vs Retained)")
    plt.xlabel(var.replace("_", " ").title())
    plt.ylabel("Density")
    plt.legend(title="Data Type")
    plt.tight_layout()
    plt.savefig(f"results/figures/kde_{var}.png", dpi=300)
    plt.close()

# Box plots
for var in ["temperature", "wind_speed", "relative_humidity"]:
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=exp, x="transmit_label", y=var)
    plt.title(f"Box Plot of {var.replace('_', ' ').title()}")
    plt.xlabel("Data Type")
    plt.ylabel(var.replace("_", " ").title())
    plt.tight_layout()
    plt.savefig(f"results/figures/box_{var}.png", dpi=300)
    plt.close()

# Correlation heatmap
plt.figure(figsize=(7, 6))
sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", square=True, cbar_kws={"shrink": 0.75})
plt.title("Pearson Correlation (Transmitted Data)")
plt.tight_layout()
plt.savefig("results/figures/correlation_heatmap.png", dpi=300)
plt.close()

# Hotspot coverage
exp_hotspot = exp[exp["hotspot"] == 1]
hotspot_transmitted = exp_hotspot["transmitted"].sum()
hotspot_total = len(exp_hotspot)
hotspot_missed = hotspot_total - hotspot_transmitted

hotspot_stats = pd.DataFrame([{
    "hotspot_total": hotspot_total,
    "hotspot_transmitted": hotspot_transmitted,
    "hotspot_missed": hotspot_missed,
    "transmission_rate": hotspot_transmitted / hotspot_total if hotspot_total > 0 else 0
}])
hotspot_stats.to_csv("results/tables/hotspot_coverage.csv", index=False)

plt.figure(figsize=(6, 6))
sns.barplot(x=["Transmitted", "Missed"], y=[hotspot_transmitted, hotspot_missed])
plt.title("Hotspot Coverage by Transmission")
plt.ylabel("Hotspot Count")
plt.tight_layout()
plt.savefig("results/figures/hotspot_coverage.png", dpi=300)
plt.close()

# Sampling rate over time
sampling_stats = tx.groupby("timestamp")["sampling_rate"].mean().reset_index()
sampling_stats.columns = ["timestamp", "avg_sampling_rate"]
sampling_stats.to_csv("results/tables/sampling_rate_over_time.csv", index=False)

plt.figure(figsize=(10, 6))
sns.lineplot(data=sampling_stats, x="timestamp", y="avg_sampling_rate")
plt.title("Average Sampling Rate Over Time")
plt.xlabel("Timestamp")
plt.ylabel("Avg Sampling Rate")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("results/figures/sampling_rate_over_time.png", dpi=300)
plt.close()

# Histogram of sampling rates
plt.figure(figsize=(8, 6))
sns.histplot(tx["sampling_rate"], bins=20, kde=True)
plt.title("Distribution of Sampling Rates")
plt.xlabel("Sampling Rate")
plt.ylabel("Frequency")
plt.tight_layout()
plt.savefig("results/figures/sampling_rate_histogram.png", dpi=300)
plt.close()
