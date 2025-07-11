import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# CONFIG
sns.set_context("talk")  # Larger fonts for presentations
plt.rcParams.update({
    "axes.titlesize": 18,
    "axes.labelsize": 16,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "legend.fontsize": 14,
    "figure.titlesize": 18
})

os.makedirs("results/figures", exist_ok=True)

# Data
metrics = ["Transmissions", "Total Data (KB)", "Total Energy (J)"]
typical = [192000, 46615, 6981]
universal = [120548, 29386, 4401]

x = np.arange(len(metrics))
width = 0.35

# Plot
fig, ax = plt.subplots(figsize=(10, 6))

bars1 = ax.bar(x - width/2, typical, width, label="Typical", color="#1f77b4")
bars2 = ax.bar(x + width/2, universal, width, label="Universal", color="#2ca02c")

ax.set_ylabel("Value")
ax.set_title("Comparison of Sensor Efficiency Metrics")
ax.set_xticks(x)
ax.set_xticklabels(metrics)
ax.legend()

ax.set_ylim(0, 210000)

# Add data labels
def add_labels(bars):
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"{int(height):,}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom')

add_labels(bars1)
add_labels(bars2)

plt.tight_layout()
plt.savefig("results/figures/sensor_efficiency_bars.png", dpi=300)
plt.show()
