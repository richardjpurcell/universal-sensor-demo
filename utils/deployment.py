import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from shapely.geometry import Point

# CONFIG
GPKG_PATH = "data/simulation.gpkg"
GRID_LAYER = "grid_cells"
OUTPUT_CSV = "results/sensor_deployment.csv"
CRS = "EPSG:3978"
TYPICAL_COUNT = 1000
UNIVERSAL_COUNT = 1000
MAX_DISTANCE_KM = 10  # Radius for sensor placement

os.makedirs("results", exist_ok=True)

def load_grid():
    grid = gpd.read_file(GPKG_PATH, layer=GRID_LAYER)
    grid = grid.to_crs(CRS)
    return grid

def get_base_station(grid):
    bounds = grid.total_bounds  # (minx, miny, maxx, maxy)
    center_x = (bounds[0] + bounds[2]) / 2
    center_y = (bounds[1] + bounds[3]) / 2
    base_station = Point(center_x, center_y)
    return base_station

def generate_sensors(base_station, count, label, crs):
    sensors = []
    for _ in range(count):
        angle = np.random.uniform(0, 2 * np.pi)
        radius = np.sqrt(np.random.uniform(0, 1)) * MAX_DISTANCE_KM * 1000  # uniform in area
        dx = radius * np.cos(angle)
        dy = radius * np.sin(angle)
        sensor_point = Point(base_station.x + dx, base_station.y + dy)
        sensors.append({
            "sensor_type": label,
            "geometry": sensor_point
        })
    return gpd.GeoDataFrame(sensors, crs=crs)

def deploy_and_save():
    grid = load_grid()
    base_station = get_base_station(grid)

    typical_sensors = generate_sensors(base_station, TYPICAL_COUNT, "typical", CRS)
    universal_sensors = generate_sensors(base_station, UNIVERSAL_COUNT, "universal", CRS)

    base_df = gpd.GeoDataFrame([{"sensor_type": "base_station", "geometry": base_station}], crs=CRS)

    all_sensors = pd.concat([typical_sensors, universal_sensors, base_df], ignore_index=True)
    all_sensors["x"] = all_sensors.geometry.x
    all_sensors["y"] = all_sensors.geometry.y

    all_sensors[["sensor_type", "x", "y"]].to_csv(OUTPUT_CSV, index=False)
    print(f"Sensor deployment saved to {OUTPUT_CSV}")

    return typical_sensors, universal_sensors, base_df

def visualize_deployment(typical, universal, base, grid):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 10))

    # Plot elevation as grayscale
    grid.plot(
        column="elevation",
        ax=ax,
        cmap="Greys_r",
        legend=True,
        legend_kwds={"label": "Elevation (m)", "shrink": 0.6},
        edgecolor="none",
    )

    # Plot sensors
    typical.plot(ax=ax, markersize=5, color="blue", label="Typical Sensors")
    universal.plot(ax=ax, markersize=5, color="green", label="Universal Sensors")

    # Plot base station as black triangle
    base.plot(
        ax=ax,
        color="yellow",
        marker="^",
        markersize=100,
        label="Base Station",
    )

    # Labels and layout
    ax.set_title("Sensor Deployment with Elevation Background", fontsize=18)
    ax.set_xlabel("X Coordinate (meters, EPSG:3978)", fontsize=16)
    ax.set_ylabel("Y Coordinate (meters, EPSG:3978)", fontsize=16)
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.set_xlim(grid.total_bounds[0], grid.total_bounds[2])
    ax.set_ylim(grid.total_bounds[1], grid.total_bounds[3])
    ax.set_aspect("equal")
    ax.legend(fontsize=14)
    plt.tight_layout()
    plt.savefig("results/sensor_deployment_map_with_elevation.png", dpi=150)
    plt.show()

if __name__ == "__main__":
    grid = load_grid()
    typical, universal, base = deploy_and_save()
    visualize_deployment(typical, universal, base, grid=grid)

