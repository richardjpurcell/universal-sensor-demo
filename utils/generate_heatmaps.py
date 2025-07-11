import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import imageio.v2 as imageio
import os
from tqdm import tqdm

# Config
GPKG_PATH = "data/simulation.gpkg"
GRID_LAYER = "grid_cells"
DATA_LAYER = "fire_simulation_data"
#VARIABLES = ["temperature", "wind_speed", "relative_humidity","fwi", "bcaod550", "omaod550"]
VARIABLES = ["hotspot"]
CRS = "EPSG:3978"
OUT_DIR = "results/output_gifs"
os.makedirs(OUT_DIR, exist_ok=True)

def load_data():
    grid = gpd.read_file(GPKG_PATH, layer=GRID_LAYER)
    grid.set_crs(CRS, inplace=True)
    data = gpd.read_file(GPKG_PATH, layer=DATA_LAYER)
    return grid, pd.DataFrame(data)

def generate_gif_for_variable(grid, data, variable):
    gif_path = os.path.join(OUT_DIR, f"{variable}.gif")
    images = []

    datetimes = sorted(data["datetime"].unique())
    for dt in tqdm(datetimes, desc=f"Rendering {variable}"):
        frame_data = data[data["datetime"] == dt][["cell_id", variable]]
        merged = grid.merge(frame_data, on="cell_id", how="left")

        fig, ax = plt.subplots(figsize=(8, 6))
        merged.plot(column=variable, ax=ax, cmap="inferno", legend=True,
                    legend_kwds={"shrink": 0.6}, edgecolor="none", missing_kwds={"color": "lightgrey"})
        ax.set_title(f"{variable} @ {dt}", fontsize=12)
        ax.axis("off")
        fig.tight_layout()

        frame_path = os.path.join(OUT_DIR, f"temp_{variable}_{dt}.png")
        fig.savefig(frame_path, dpi=100)
        plt.close(fig)
        images.append(imageio.imread(frame_path))
        os.remove(frame_path)

    imageio.mimsave(gif_path, images, duration=0.5)
    print(f"Saved GIF to {gif_path}")

def generate_hotspot_visualization(grid, data, output_gif="results/hotspots.gif"):
    import imageio.v2 as imageio
    from shapely.geometry import Point
    import matplotlib.pyplot as plt
    from tqdm import tqdm
    import matplotlib.cm as cm
    import numpy as np
    import os

    os.makedirs("results", exist_ok=True)

    # Prepare decay tracking
    unique_timesteps = sorted(data["datetime"].unique())
    decay_map = {}  # cell_id -> remaining_decay (max 10)

    images = []

    for i, dt in enumerate(tqdm(unique_timesteps, desc="Rendering hotspots")):
        frame_data = data[data["datetime"] == dt]
        new_hotspots = frame_data[frame_data["hotspot"] == 1]

        # Update decay
        for cid in new_hotspots["cell_id"]:
            decay_map[cid] = 10  # visible 3 timesteps + fade 7

        # Decay all values
        for cid in list(decay_map):
            decay_map[cid] -= 1
            if decay_map[cid] <= 0:
                del decay_map[cid]

        # Assign visual intensity based on decay
        grid_copy = grid.copy()
        grid_copy["hotspot_intensity"] = grid_copy["cell_id"].map(decay_map).fillna(0)

        # Optional: buffer + dissolve for cloud effect
        cloud = grid_copy[grid_copy["hotspot_intensity"] > 0].copy()
        if not cloud.empty:
            cloud["geometry"] = cloud.buffer(300)  # 300m halo
            cloud = cloud.dissolve()  # merge into single polygon

        # Plot
        fig, ax = plt.subplots(figsize=(8, 6))
        base = grid.plot(ax=ax, color="lightgrey", edgecolor="none")
        grid_copy.plot(
            column="hotspot_intensity",
            cmap="Reds",
            ax=ax,
            vmin=0,
            vmax=10,
            edgecolor="none",
            legend=False,
        )
        if not cloud.empty:
            cloud.plot(facecolor="none", edgecolor="orange", linewidth=0.8, ax=ax)

        grid.dissolve().boundary.plot(ax=ax, edgecolor="black", linewidth=0.5)

        ax.set_title(f"Hotspots @ {dt}")
        ax.set_axis_off()
        plt.tight_layout()

        frame_path = f"results/output_gifs/frame_hotspot_{i:04d}.png"
        fig.savefig(frame_path, dpi=100)
        plt.close(fig)
        images.append(imageio.imread(frame_path))
        os.remove(frame_path)

    imageio.mimsave(output_gif, images, duration=0.5)
    print(f"Saved hotspot animation to {output_gif}")


def main():
    grid, data = load_data()

    for variable in VARIABLES:
        if variable == "hotspot":
            generate_hotspot_visualization(grid, data)
        else:
            generate_gif_for_variable(grid, data, variable)

if __name__ == "__main__":
    main()

