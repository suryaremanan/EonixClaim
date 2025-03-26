"""
Inspector utility for examining Agentforce state and behavior.
"""
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
load_dotenv()

# Import relevant modules
from salesforce.agentforce import AgentforceManager
from slack_sdk import WebClient

# Create a directory for inspections
os.makedirs("inspections", exist_ok=True)

# Initialize components
agentforce = AgentforceManager()
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
channel_id = "C08HJ6LA9MM"  # Your channel ID

# Generate test data (similar to what comes from YOLO + Telematics + Fraud detection)
test_data = {
    "damaged_parts": ["windshield", "front bumper"],
    "damages": ["crack", "dent"],
    "severity": "Moderate",
    "severity_score": 0.65,
    "estimated_repair_cost": 1450.75,
    "fraud_rating": "Low",
    "fraud_probability": 0.12,
    "fraud_flags": []
}

# Get timestamp for inspection ID
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
inspection_file = f"inspections/agentforce_inspection_{timestamp}.json"

# Generate the Einstein response
claim_id = f"INSPECT-{timestamp}"
response_blocks = agentforce._simulate_einstein_gpt_response(test_data)

# Record the inspection results
inspection = {
    "timestamp": timestamp,
    "input_data": test_data,
    "simulated_einstein_response": response_blocks,
    "agentforce_methods": {
        "trigger_claim_processing_agent": {
            "description": "Triggers the claim processing with simulated Einstein GPT enhancement",
            "parameters": ["claim_id", "damage_report", "channel_id", "client"],
            "returns": "Boolean indicating success"
        },
        "_simulate_einstein_gpt_response": {
            "description": "Simulates an Einstein GPT response locally",
            "parameters": ["damage_report"],
            "returns": "Slack blocks for formatted message"
        }
    }
}

# Save inspection to file
with open(inspection_file, "w") as f:
    json.dump(inspection, f, indent=2)

print(f"Agentforce inspection saved to {inspection_file}")

# Optionally send the response to Slack for verification
should_send = input("Send this response to Slack? (y/n): ").lower() == 'y'
if should_send:
    result = client.chat_postMessage(
        channel=channel_id,
        blocks=response_blocks,
        text="AI-Enhanced Damage Analysis (Inspection)"
    )
    print(f"Message sent to Slack: {result['ts']}") 