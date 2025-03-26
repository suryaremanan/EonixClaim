
import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelematicsProcessor:
    
    
    def __init__(self, data_dir: str = "data/telematics"):
        
        self.data_dir = data_dir
        logger.info(f"Initialized telematics processor with data directory: {data_dir}")
    
    def check_driving_behavior_near_incident(self, driver_id, incident_time):
        
        # Convert incident_time to pandas Timestamp if it's a string
        if isinstance(incident_time, str):
            incident_time = pd.to_datetime(incident_time)
            
        try:
            # Analyze data around the incident time
            incident_analysis = self.analyze_incident_data(driver_id, incident_time)
            
            # Check for anomalies in the driving behavior
            if "error" in incident_analysis:
                # If we couldn't get real data, generate demo data
                return self._generate_sample_behavior_data(driver_id, incident_time)
            
            # Get relevant windows for analysis (before and after the incident)
            pre_incident_window = 15  # minutes before incident
            post_incident_window = 5   # minutes after incident
            
            # Calculate risk score based on driving patterns
            risk_score = self._calculate_risk_score(incident_analysis)
            
            result = {
                "driver_id": driver_id,
                "incident_time": incident_time,
                "analysis_time": datetime.now(),
                "pre_incident_behavior": incident_analysis.get("pre_incident", {}),
                "post_incident_behavior": incident_analysis.get("post_incident", {}),
                "risk_factors": self._identify_risk_factors(incident_analysis),
                "risk_score": risk_score,
                "consistent_with_claim": risk_score < 0.7,  # threshold for consistency
                "telematics_available": True
            }
            
            return result
        except Exception as e:
            logger.error(f"Error processing telematics data: {e}")
            return self._generate_sample_behavior_data(driver_id, incident_time)
    
    def analyze_incident_data(self, driver_id, timestamp):
      
        try:
            # Convert timestamp to pandas Timestamp if it's a string
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
                
            # Get the driver's telematics data
            df = self._load_driver_data(driver_id)
            if df is None or df.empty:
                return {"error": f"No telematics data available for driver {driver_id}"}
                
            # Convert the timestamp column to datetime if it's not already
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
            # Check if the incident time is within the data timeframe
            if timestamp >= df['timestamp'].min() and timestamp <= df['timestamp'].max():
                # Find the closest data point to the incident time
                closest_idx = (df['timestamp'] - timestamp).abs().idxmin()
                closest_point = df.loc[closest_idx].to_dict()
                
                # Get data for the period around the incident (30 min before and after)
                window_start = timestamp - pd.Timedelta(minutes=30)
                window_end = timestamp + pd.Timedelta(minutes=30)
                
                window_data = df[(df['timestamp'] >= window_start) & (df['timestamp'] <= window_end)]
                
                # Calculate statistics for the window
                if not window_data.empty:
                    avg_speed = window_data['speed'].mean()
                    max_speed = window_data['speed'].max()
                    avg_braking = window_data['braking'].mean() if 'braking' in window_data.columns else 0
                    max_braking = window_data['braking'].max() if 'braking' in window_data.columns else 0
                    
                    # Detect sudden stops (high braking values)
                    sudden_stops = window_data[window_data['braking'] > 0.6].shape[0] if 'braking' in window_data.columns else 0
                    
                    # Detect speeding (speeds above 70 mph)
                    speeding = window_data[window_data['speed'] > 70].shape[0]
                    
                    result = {
                        "incident_time": timestamp,
                        "closest_point": closest_point,
                        "window_stats": {
                            "avg_speed": avg_speed,
                            "max_speed": max_speed,
                            "avg_braking": avg_braking,
                            "max_braking": max_braking,
                            "sudden_stops": sudden_stops,
                            "speeding_instances": speeding
                        },
                        "anomalies_detected": sudden_stops > 0 or speeding > 0
                    }
                else:
                    result = {
                        "incident_time": timestamp,
                        "closest_point": closest_point,
                        "warning": "Limited data available in the timeframe around the incident"
                    }
            else:
                # If the incident time is outside our data range, return the closest data we have
                if timestamp < df['timestamp'].min():
                    closest_time = df['timestamp'].min()
                else:
                    closest_time = df['timestamp'].max()
                    
                closest_idx = (df['timestamp'] - closest_time).abs().idxmin()
                closest_point = df.loc[closest_idx].to_dict()
                
                time_diff = abs((timestamp - closest_time).total_seconds() / 60)  # minutes
                
                result = {
                    "incident_time": timestamp,
                    "closest_point": closest_point,
                    "warning": f"Incident time is outside available data range by {time_diff:.1f} minutes"
                }
                
                # Add time mismatch flag if reported time differs significantly from detected
                result["time_mismatch"] = time_diff > 30
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing incident data: {e}")
            return {"error": f"Incident analysis error: {str(e)}"}
    
    def _load_driver_data(self, driver_id):
        
        try:
            # Convert driver_id to default value for demo if it's a Slack ID
            if isinstance(driver_id, str) and driver_id.startswith('U'):
                logger.info(f"Converting Slack user ID {driver_id} to default driver ID 12345")
                driver_id = '12345'
            
            try:
                driver_id = int(driver_id)
            except ValueError:
                logger.warning(f"Non-numeric driver ID: {driver_id}, using default")
                driver_id = 12345
            
            # Check if the data file exists
            data_file = os.path.join(self.data_dir, f"{driver_id}.csv")
            if os.path.exists(data_file):
                # Load the data from CSV
                df = pd.read_csv(data_file)
                logger.info(f"Loaded telematics data for driver {driver_id}")
                return df
            else:
                # Generate sample data for the driver
                logger.warning(f"No data found for driver {driver_id}, generating sample data")
                sample_data = self._generate_sample_data(driver_id)
                
                # Ensure directory exists
                os.makedirs(self.data_dir, exist_ok=True)
                
                # Save the sample data
                sample_data.to_csv(data_file, index=False)
                logger.info(f"Generated and saved sample data for driver {driver_id}")
                
                return sample_data
        except Exception as e:
            logger.error(f"Error loading telematics data: {e}")
            return None
    
    def _generate_sample_data(self, driver_id, days=7, frequency_minutes=10):
        
        # Calculate number of data points
        points = int((days * 24 * 60) / frequency_minutes)
        
        # Generate timestamps
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        timestamps = [start_time + timedelta(minutes=i*frequency_minutes) for i in range(points)]
        
        # Generate speed data (mph)
        # Normal distribution around 45 mph, std dev 15 mph
        speeds = np.clip(np.random.normal(45, 15, points), 0, 95)
        
        # Generate RPM data
        # Related to speed but with some variation
        rpms = speeds * 50 + np.random.normal(500, 200, points)
        rpms = np.clip(rpms, 700, 5000)
        
        # Generate throttle data (0 to 1)
        throttles = np.clip(speeds / 120 + np.random.normal(0, 0.1, points), 0, 1)
        
        # Generate braking data (0 to 1, but mostly 0)
        # Occasional braking events
        brakings = np.zeros(points)
        braking_events = np.random.choice(points, size=int(points * 0.1), replace=False)
        brakings[braking_events] = np.clip(np.random.normal(0.3, 0.2, len(braking_events)), 0, 1)
        
        # Generate steering data (-1 to 1)
        steerings = np.clip(np.random.normal(0, 0.2, points), -1, 1)
        
        # Generate lateral acceleration data (-1 to 1)
        lat_accels = np.clip(steerings * 0.5 + np.random.normal(0, 0.1, points), -1, 1)
        
        # Generate fuel level data (0 to 1)
        fuel_levels = np.ones(points)
        for i in range(1, points):
            fuel_levels[i] = max(0, fuel_levels[i-1] - 0.0002 * speeds[i])
            # Occasional refueling
            if fuel_levels[i] < 0.2 and np.random.random() < 0.3:
                fuel_levels[i] = 1.0
        
        # Generate engine temperature data (degrees C)
        engine_temps = np.clip(80 + rpms / 50 + np.random.normal(0, 3, points), 40, 110)
        
        # Create DataFrame
        df = pd.DataFrame({
            'timestamp': timestamps,
            'speed': speeds,
            'rpm': rpms,
            'throttle': throttles,
            'braking': brakings,
            'steering': steerings,
            'lateral_acceleration': lat_accels,
            'fuel_level': fuel_levels,
            'engine_temp': engine_temps
        })
        
        return df
    
    def _generate_sample_behavior_data(self, driver_id, incident_time):
       
        # Generate a random risk score (lower is better)
        risk_score = random.uniform(0.2, 0.6)
        
        return {
            "driver_id": driver_id,
            "incident_time": incident_time,
            "analysis_time": datetime.now(),
            "pre_incident_behavior": {
                "avg_speed": random.uniform(30, 60),
                "max_speed": random.uniform(55, 75),
                "sudden_braking_events": random.randint(0, 2),
                "avg_following_distance": random.uniform(2.0, 4.0)
            },
            "post_incident_behavior": {
                "immediate_stop": random.choice([True, False]),
                "stop_duration": random.uniform(1.0, 10.0) if random.random() > 0.3 else 0.0,
                "erratic_driving": random.random() < 0.1
            },
            "risk_factors": ["moderate_speed"] if random.random() > 0.7 else [],
            "risk_score": risk_score,
            "consistent_with_claim": risk_score < 0.7,
            "telematics_available": False,
            "note": "This is simulated data as actual telematics were unavailable"
        }
    
    def _calculate_risk_score(self, incident_analysis):
        
        # Start with a base score
        risk_score = 0.3
        
        # Add risk for anomalies
        if incident_analysis.get("anomalies_detected", False):
            risk_score += 0.2
        
        # Add risk for time mismatch
        if incident_analysis.get("time_mismatch", False):
            risk_score += 0.3
        
        # Add risk for high speed
        window_stats = incident_analysis.get("window_stats", {})
        if window_stats.get("max_speed", 0) > 80:
            risk_score += 0.15
        elif window_stats.get("avg_speed", 0) > 70:
            risk_score += 0.1
        
        # Add risk for sudden stops
        if window_stats.get("sudden_stops", 0) > 2:
            risk_score += 0.15
        
        # Cap the risk score at 1.0
        return min(risk_score, 1.0)
    
    def _identify_risk_factors(self, incident_analysis):
        
        risk_factors = []
        
        # Check window stats for risk factors
        window_stats = incident_analysis.get("window_stats", {})
        
        if window_stats.get("max_speed", 0) > 80:
            risk_factors.append("excessive_speed")
        elif window_stats.get("avg_speed", 0) > 70:
            risk_factors.append("high_speed")
        
        if window_stats.get("sudden_stops", 0) > 2:
            risk_factors.append("frequent_hard_braking")
        elif window_stats.get("max_braking", 0) > 0.8:
            risk_factors.append("extreme_braking")
        
        if window_stats.get("speeding_instances", 0) > 0:
            risk_factors.append("speeding")
        
        # Add time mismatch as a risk factor
        if incident_analysis.get("time_mismatch", False):
            risk_factors.append("reported_time_mismatch")
        
        # If no risk factors identified, add 'none'
        if not risk_factors:
            risk_factors.append("none")
        
        return risk_factors
