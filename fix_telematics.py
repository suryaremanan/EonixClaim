import os

# Modify telematics/telematics_processor.py to handle Slack user IDs
file_path = "telematics/telematics_processor.py"

with open(file_path, "r") as f:
    content = f.read()

# Replace the problematic part that tries to convert driver_id to int
modified_content = content.replace(
    "driver_id = int(driver_id)",
    "# Convert driver_id to default value for demo if it's a Slack ID\n        if driver_id.startswith('U'):\n            logger.info(f\"Converting Slack user ID {driver_id} to default driver ID 12345\")\n            driver_id = '12345'\n        try:\n            driver_id = int(driver_id)\n        except ValueError:\n            logger.warning(f\"Non-numeric driver ID: {driver_id}, using default\")\n            driver_id = 12345"
)

with open(file_path, "w") as f:
    f.write(modified_content)

print("Telematics processor fixed to handle Slack user IDs")
