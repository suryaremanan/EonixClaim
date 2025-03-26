import os

# Modify slack/handlers/damage_assessment_handler.py to map Slack user IDs to driver IDs
file_path = "slack/handlers/damage_assessment_handler.py"

with open(file_path, "r") as f:
    content = f.read()

# Add function to map Slack user IDs to driver IDs
mapping_function = """
def map_slack_to_driver_id(slack_user_id):
    
    # In a real system, this would query a database
    # For demo, we'll use a hardcoded mapping
    mapping = {
        # Add your actual Slack user ID here
        "U07R1MDV0TD": "12345"
    }
    return mapping.get(slack_user_id, "12345")  # Default to 12345 if not found
"""

# Add the function after the imports
content = content.replace(
    "# Track processed files to prevent duplicates", 
    mapping_function + "\n\n# Track processed files to prevent duplicates"
)

# Modify the process_file function to use the mapping
content = content.replace(
    'driver_id = user_id',
    'driver_id = map_slack_to_driver_id(user_id)'
)

with open(file_path, "w") as f:
    f.write(content)

print("Damage assessment handler fixed to map Slack user IDs to driver IDs")
