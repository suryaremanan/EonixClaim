"""
Fix timestamp comparison in telematics processor.
"""
import os

# Path to the telematics processor file
file_path = "telematics/telematics_processor.py"

with open(file_path, "r") as f:
    content = f.read()

# Fix the timestamp comparison issue
# The error is: '>=' not supported between instances of 'str' and 'Timestamp'
# This happens when trying to compare a string timestamp with a pandas Timestamp

# Replace string timestamp comparisons with proper datetime conversion
modified_content = content.replace(
    "if timestamp >= df['timestamp'].min() and timestamp <= df['timestamp'].max():",
    "# Convert timestamp to pandas Timestamp if it's a string\n            if isinstance(timestamp, str):\n                timestamp = pd.to_datetime(timestamp)\n            if timestamp >= df['timestamp'].min() and timestamp <= df['timestamp'].max():"
)

# Also fix potential string comparison when finding closest time
modified_content = modified_content.replace(
    "abs(df['timestamp'] - timestamp)",
    "abs(df['timestamp'] - pd.to_datetime(timestamp) if isinstance(timestamp, str) else timestamp)"
)

# Write the fixed content back to the file
with open(file_path, "w") as f:
    f.write(modified_content)

print(f"Fixed timestamp comparison issues in {file_path}")

# Additionally, make sure any other timestamp-related functions are fixed
file_path = "telematics/telematics_processor.py"

with open(file_path, "r") as f:
    content = f.read()

# Ensure all timestamp parameters are properly converted to datetime objects
modified_content = content.replace(
    "def check_driving_behavior_near_incident(self, driver_id, incident_time):",
    "def check_driving_behavior_near_incident(self, driver_id, incident_time):\n        # Convert incident_time to pandas Timestamp if it's a string\n        if isinstance(incident_time, str):\n            import pandas as pd\n            incident_time = pd.to_datetime(incident_time)"
)

# Write the fixed content back to the file
with open(file_path, "w") as f:
    f.write(modified_content)

print(f"Added timestamp conversion in check_driving_behavior_near_incident function") 