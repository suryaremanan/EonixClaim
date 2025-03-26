import os
import re

# Path to the telematics processor file
file_path = "telematics/telematics_processor.py"

with open(file_path, "r") as f:
    content = f.read()

# Add pandas import if needed
if "import pandas as pd" not in content:
    content = content.replace(
        "import logging",
        "import logging\nimport pandas as pd"
    )

# Replace the analyze_incident_data method entirely
analyze_incident_pattern = re.compile(r"def analyze_incident_data\(.*?def ", re.DOTALL)
analyze_incident_match = analyze_incident_pattern.search(content)

if analyze_incident_match:
    old_method = analyze_incident_match.group(0)
    new_method = """def analyze_incident_data(self, driver_id, timestamp):
        
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
                    avg_braking = window_data['braking'].mean() if 'braking' in window_data else 0
                    max_braking = window_data['braking'].max() if 'braking' in window_data else 0
                    
                    # Detect sudden stops (high braking values)
                    sudden_stops = window_data[window_data['braking'] > 0.6].shape[0] if 'braking' in window_data else 0
                    
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
            result["time_mismatch"] = time_diff > 30 if 'time_diff' in locals() else False
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing incident data: {e}")
            return {"error": f"Incident analysis error: {str(e)}"}
            
    def """
    
    # Replace the method
    new_content = content.replace(old_method, new_method)
    
    with open(file_path, "w") as f:
        f.write(new_content)
    
    print("Replaced analyze_incident_data method with fixed version") 