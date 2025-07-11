import pandas as pd
from shapely.geometry import Point
import geopandas as gpd
import json
import numpy as np
from scipy.stats import entropy
import os
from utils.path_loss import compute_path_loss_db

class UniversalSensor:
    def __init__(self, sensor_id, x, y, base_x, base_y):
        self.sensor_id = sensor_id
        self.location = Point(x, y)
        self.readings = pd.DataFrame()

        self.base_x = base_x
        self.base_y = base_y

        # Placeholder internal state
        self.predicted_state = None
        self.current_config = {"resolution": 1.0, "sampling_rate": 1.0}
        self.memory = []  # for storing prediction errors, feedback, etc.

        #entropy
        self.error_history = []
        self.max_error_history = 10  # sliding window

        self.kl_threshold = float(os.getenv("KL_THRESHOLD", 1.0))
        self.max_error_history = int(os.getenv("ERROR_HISTORY", 20))


    def sense(self, timestep_gdf, log=True):
        if timestep_gdf.empty:
            return None

        # Create a GeoDataFrame for the sensor point
        sensor_gdf = gpd.GeoDataFrame(
            [{"sensor_id": self.sensor_id}],
            geometry=[self.location],
            crs=timestep_gdf.crs
        )

        # Spatial join to find the grid cell containing the sensor
        match = gpd.sjoin(sensor_gdf, timestep_gdf, how="left", predicate="within")
        if match.empty:
            return None

        reading = match.iloc[0].to_dict()
        # Explicitly keep key environmental variables
        env_vars = ["temperature", "wind_speed", "relative_humidity", "hotspot", "fwi"]

        reading["x"] = self.location.x
        reading["y"] = self.location.y
        reading = {k: reading.get(k, None) for k in env_vars + ["x", "y", "geometry", "datetime", "sensor_id"]}

        if log:
            self.readings = pd.concat([self.readings, pd.DataFrame([reading])], ignore_index=True)


        return reading


    def predict(self):
        # Placeholder: naive prediction from previous values
        if not self.readings.empty:
            self.predicted_state = self.readings.iloc[-1]
        else:
            self.predicted_state = None
        return self.predicted_state

    def compute_prediction_error(self, current_obs, variables=("temperature", "wind_speed", "relative_humidity")):
        if self.predicted_state is None or current_obs is None:
            return None

        errors = {}
        for var in variables:
            if var in current_obs and var in self.predicted_state:
                errors[var] = abs(current_obs[var] - self.predicted_state[var])
        return errors

    def kl_divergence_gaussians(self, mu_p, mu_q, sigma=1.0):
        """KL(P‖Q): P = predicted, Q = observed"""
        return (0.5 / sigma**2) * (mu_p - mu_q)**2



    def compare(self, observation):
        if self.predicted_state is None or observation is None:
            return None
        prediction_error = {}
        for key in ["temperature", "wind_speed", "relative_humidity"]:
            if key in observation and key in self.predicted_state:
                prediction_error[key] = observation[key] - self.predicted_state[key]
        
        self.memory.append(prediction_error)

        # Store mean error for entropy calculation
        if prediction_error:
            mean_err = sum(abs(v) for v in prediction_error.values()) / len(prediction_error)
            self.error_history.append(mean_err)
            if len(self.error_history) > self.max_error_history:
                self.error_history.pop(0)

        return prediction_error


    def update_control(self, prediction_error):
        # Placeholder control policy: increase sampling if high error
        if not prediction_error:
            return
        mean_error = sum(abs(v) for v in prediction_error.values()) / len(prediction_error)
        if mean_error > 2.0:
            self.current_config["sampling_rate"] *= 1.2
        else:
            self.current_config["sampling_rate"] *= 0.9

    def update_sampling_rate(self):
        if not self.error_history:
            return

        # Normalize error distribution
        hist = np.array(self.error_history)
        probs = hist / hist.sum()
        entropy_value = -np.sum(probs * np.log2(probs + 1e-9))

        # Entropy range tuning: max entropy ~ log2(n)
        max_entropy = np.log2(self.max_error_history)
        norm_entropy = entropy_value / max_entropy  # 0 to 1

        # Linear control policy: more entropy → more sampling
        self.current_config["sampling_rate"] = 0.2 + 0.8 * norm_entropy


    def step(self, timestep_gdf):
        self.predict()

        # Decide whether to sample this timestep
        if np.random.rand() > self.current_config["sampling_rate"]:
            #print(f"Sensor {self.sensor_id} skipped sensing this timestep (sampling rate = {self.current_config['sampling_rate']:.2f})")
            return

        # Proceed with sensing
        observation = self.sense(timestep_gdf, log=True)

        # Compare to prediction
        error = self.compare(observation)

        # Update control strategy (sampling rate from prediction error)
        self.update_control(error)

        # Update sampling rate based on entropy of recent errors
        self.update_sampling_rate()

        # Debug output for entropy-based adaptation
        #print(f"Sensor {self.sensor_id} | Sampling rate = {self.current_config['sampling_rate']:.2f}")


    def transmit(self, bitrate_bps=5470, power_watts=0.1):
        #print(f"[DEBUG] Universal Sensor {self.sensor_id} readings length: {len(self.readings)}")


        if self.readings.empty:
            return None

        latest = self.readings.iloc[-1]
        latest_dict = latest.to_dict()

        if not self.should_transmit(latest_dict):
            return None

        # Clean serialization
        geom = latest_dict.pop("geometry", None)
        if geom:
            latest_dict["geometry"] = (geom.x, geom.y)
        if "datetime" in latest_dict and isinstance(latest_dict["datetime"], pd.Timestamp):
            latest_dict["datetime"] = latest_dict["datetime"].isoformat()

        payload_json = json.dumps(latest_dict)
        payload_size_bytes = len(payload_json.encode("utf-8"))
        payload_size_bits = payload_size_bytes * 8
        tx_time_sec = payload_size_bits / bitrate_bps

        #base_x = 0  # Replace with your actual base station x
        #base_y = 0
        path_loss_db = compute_path_loss_db(self.location.x, self.location.y, self.base_x, self.base_y)

        # ✅ Convert base power to dBm and apply path loss
        path_loss_multiplier = min(10 ** (path_loss_db / 10), 1e9)  # cap to 1000×
        adjusted_power_watts = power_watts * path_loss_multiplier


        energy_mJ = adjusted_power_watts * tx_time_sec * 1000

        #print(f"[DEBUG] Payload preview: {latest_dict}")


        return {
            "sensor_id": self.sensor_id,
            "timestamp": latest_dict["datetime"],
            "data_sent_bytes": payload_size_bytes,
            "tx_time_sec": tx_time_sec,
            "energy_used_mJ": energy_mJ,
            "x": self.location.x,
            "y": self.location.y,
            "sampling_rate": self.current_config["sampling_rate"],  # ✅ Added here
            "temperature": latest_dict.get("temperature"),
            "wind_speed": latest_dict.get("wind_speed"),
            "relative_humidity": latest_dict.get("relative_humidity"),
            "hotspot": latest_dict.get("hotspot"),
            "fwi": latest_dict.get("fwi")
        }



    def should_transmit(self, current_obs, threshold=None):
        threshold = threshold if threshold is not None else self.kl_threshold

        if self.predicted_state is None or current_obs is None:
            return False

        total_kl = 0.0
        count = 0
        sigma = 1.0  # assumed standard deviation for all variables

        for var in ["temperature", "wind_speed", "relative_humidity"]:
            if var in self.predicted_state and var in current_obs:
                mu_p = self.predicted_state[var]
                mu_q = current_obs[var]
                kl = self.kl_divergence_gaussians(mu_p, mu_q, sigma)
                total_kl += kl
                count += 1

        if count == 0:
            return False

        avg_kl = total_kl / count

        # ✅ Debugging output
        #print(f"Sensor {self.sensor_id} | avg_KL = {avg_kl:.3f} | Transmit: {avg_kl > threshold}")

        return avg_kl > threshold


    def __repr__(self):
        return f"UniversalSensor(id={self.sensor_id}, x={self.location.x:.2f}, y={self.location.y:.2f})"
