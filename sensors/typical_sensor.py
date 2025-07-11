import pandas as pd
from shapely.geometry import Point
import geopandas as gpd
import json
import numpy as np
from utils.path_loss import compute_path_loss_db


class TypicalSensor:
    def __init__(self, sensor_id, x, y, base_x, base_y):
        self.sensor_id = sensor_id
        self.location = Point(x, y)
        self.readings = pd.DataFrame()

        self.base_x = base_x
        self.base_y = base_y

    def read_from_simulation(self, timestep_gdf, log=True):
        # Ensure both are in GeoDataFrames with same CRS
        sensor_gdf = gpd.GeoDataFrame(
            [{"sensor_id": self.sensor_id}],
            geometry=[self.location],
            crs=timestep_gdf.crs
        )

        match = gpd.sjoin(sensor_gdf, timestep_gdf, how="left", predicate="within")
        if match.empty:
            return None

        env_vars = ["temperature", "wind_speed", "relative_humidity", "hotspot", "fwi"]
        raw = match.iloc[0].to_dict()
        reading = {k: raw.get(k, None) for k in env_vars + ["datetime", "geometry"]}
        reading["sensor_id"] = self.sensor_id
        reading["x"] = self.location.x
        reading["y"] = self.location.y


        if log:
            self.readings = pd.concat([self.readings, pd.DataFrame([reading])], ignore_index=True)

        return reading


    def get_time_series(self, variable):
        if variable in self.readings.columns:
            return self.readings[["datetime", variable]]
        else:
            return pd.DataFrame(columns=["datetime", variable])

    def transmit(self, bitrate_bps=5470, power_watts=0.1):
        #print(f"[DEBUG] Sensor {self.sensor_id} preparing to transmit. Total readings: {len(self.readings)}")

        if self.readings.empty:
            return None

        latest = self.readings.iloc[-1]
        payload_dict = latest.to_dict()

        # Clean up non-serializable fields
        geom = payload_dict.pop("geometry", None)
        if geom:
            payload_dict["geometry"] = (geom.x, geom.y)

        if "datetime" in payload_dict and isinstance(payload_dict["datetime"], pd.Timestamp):
            payload_dict["datetime"] = payload_dict["datetime"].isoformat()

        payload_json = json.dumps(payload_dict)
        payload_size_bytes = len(payload_json.encode("utf-8"))
        payload_size_bits = payload_size_bytes * 8

        tx_time_sec = payload_size_bits / bitrate_bps

        #base_x = 0  # Replace with your actual base station x
        #base_y = 0  # Replace with your actual base station y

        path_loss_db = compute_path_loss_db(self.location.x, self.location.y, self.base_x, self.base_y)

        # ✅ Convert base power to dBm and apply path loss
        path_loss_multiplier = min(10 ** (path_loss_db / 10), 1e9)  # cap to 1000×
        adjusted_power_watts = power_watts * path_loss_multiplier


        energy_mJ = adjusted_power_watts * tx_time_sec * 1000

        #print(f"[DEBUG] Payload keys: {list(payload_dict.keys())}")

        return {
            "sensor_id": self.sensor_id,
            "timestamp": payload_dict["datetime"],
            "data_sent_bytes": payload_size_bytes,
            "tx_time_sec": tx_time_sec,
            "energy_used_mJ": energy_mJ,
            "x": self.location.x,
            "y": self.location.y,
            "temperature": payload_dict.get("temperature"),
            "wind_speed": payload_dict.get("wind_speed"),
            "relative_humidity": payload_dict.get("relative_humidity"),
            "hotspot": payload_dict.get("hotspot"),
            "fwi": payload_dict.get("fwi")
        }




    def __repr__(self):
        return f"TypicalSensor(id={self.sensor_id}, x={self.location.x:.2f}, y={self.location.y:.2f})"
