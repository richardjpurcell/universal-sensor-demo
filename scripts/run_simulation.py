
import geopandas as gpd
import pandas as pd
import os
from shapely.geometry import Point
from sensors.typical_sensor import TypicalSensor
from sensors.universal_sensor import UniversalSensor

SENSOR_CSV = "results/sensor_deployment.csv"
SIM_GPKG = "data/simulation.gpkg"
SIM_LAYER = "fire_simulation_data"
RESULT_CSV = "results/experiment_log_combined.csv"
TRANSMISSION_CSV = "results/transmission_log_combined.csv"
CRS = "EPSG:3978"

def load_sensors(sensor_csv_path, base_x, base_y):
    df = pd.read_csv(sensor_csv_path)
    sensors = []

    for i, row in df.iterrows():
        if row["sensor_type"] == "typical":
            sensor = TypicalSensor(sensor_id=i, x=row["x"], y=row["y"], base_x=base_x, base_y=base_y)
        elif row["sensor_type"] == "universal":
            sensor = UniversalSensor(sensor_id=i, x=row["x"], y=row["y"], base_x=base_x, base_y=base_y)
        else:
            continue
        sensors.append(sensor)
    return sensors


def load_simulation_data():
    fire_df = gpd.read_file(SIM_GPKG, layer=SIM_LAYER)
    grid = gpd.read_file(SIM_GPKG, layer="grid_cells")

    fire_df["cell_id"] = fire_df["cell_id"].astype(int)
    grid["cell_id"] = grid["cell_id"].astype(int)
    grid = grid.to_crs(CRS)

    sim_df = grid.merge(fire_df, on="cell_id")
    sim_df["datetime"] = pd.to_datetime(sim_df["datetime"])
    return sim_df

def run_simulation():
    os.makedirs("results", exist_ok=True)

    sensor_df = pd.read_csv(SENSOR_CSV)

    base_x = sensor_df["x"].mean()
    base_y = sensor_df["y"].mean()

    sensors = load_sensors(SENSOR_CSV, base_x, base_y)

    sim_data = load_simulation_data()

    start = pd.to_datetime(os.getenv("SIM_START", "2016-05-01 00:00:00"))
    end = pd.to_datetime(os.getenv("SIM_END", "2016-05-08 23:00:00"))

    timesteps = sorted(sim_data["datetime"].unique())
    timesteps = [ts for ts in timesteps if start <= ts <= end]

    logs = []
    transmission_logs = []

    for timestep in timesteps:
        timestep_df = sim_data[sim_data["datetime"] == timestep]

        for sensor in sensors:
            if isinstance(sensor, TypicalSensor):
                reading = sensor.read_from_simulation(timestep_df)
                if reading is not None:
                    logs.append({
                        "sensor_id": sensor.sensor_id,
                        "sensor_type": "typical",
                        "datetime": timestep,
                        "x": sensor.location.x,
                        "y": sensor.location.y,
                        "temperature": reading.get("temperature"),
                        "wind_speed": reading.get("wind_speed"),
                        "relative_humidity": reading.get("relative_humidity"),
                        "hotspot": reading.get("hotspot"),
                        "fwi": reading.get("fwi")
                    })
                    transmission = sensor.transmit()
                    if transmission:
                        transmission["sensor_type"] = "typical"
                        transmission_logs.append(transmission)

            elif isinstance(sensor, UniversalSensor):
                sensor.step(timestep_df)
                reading = sensor.readings.iloc[-1].to_dict() if not sensor.readings.empty else None
                if reading is not None:
                    logs.append({
                        "sensor_id": sensor.sensor_id,
                        "sensor_type": "universal",
                        "datetime": timestep,
                        "x": sensor.location.x,
                        "y": sensor.location.y,
                        "temperature": reading.get("temperature"),
                        "wind_speed": reading.get("wind_speed"),
                        "relative_humidity": reading.get("relative_humidity"),
                        "hotspot": reading.get("hotspot"),
                        "fwi": reading.get("fwi")
                    })
                    transmission = sensor.transmit()
                    if transmission:
                        transmission["sensor_type"] = "universal"
                        transmission_logs.append(transmission)

        print(f"Timestep: {timestep} - Sensors updated")

    # Save experiment results
    pd.DataFrame(logs).to_csv(RESULT_CSV, index=False)
    print(f"Experiment log saved to {RESULT_CSV}")

    # Save transmission logs
    if transmission_logs:
        pd.DataFrame(transmission_logs).to_csv(TRANSMISSION_CSV, index=False)
        print(f"Transmission log saved to {TRANSMISSION_CSV}")

if __name__ == "__main__":
    run_simulation()
