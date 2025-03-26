
import os
import sys
from dotenv import load_dotenv
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

# Import required modules
from image_processing.vehicle_parts_detector import VehicleDamageDetector
from telematics.telematics_processor import TelematicsProcessor
from fraud_detection.fraud_detector import FraudDetector
from salesforce.agentforce import AgentforceManager
from slack_sdk import WebClient

# Initialize components
damage_detector = VehicleDamageDetector()
telematics_processor = TelematicsProcessor()
fraud_detector = FraudDetector()
agentforce = AgentforceManager()
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
channel_id = "C08HJ6LA9MM"  # Your channel ID

# Test image path - modify this to point to a valid test image
test_image = "test_car_damage.jpg"
if not os.path.exists(test_image):
    print(f"Test image not found: {test_image}")
    print("Using a simulated damage report instead")
    assessment = {
        "status": "success",
        "damaged_parts": ["windshield", "front bumper"],
        "severity": "Moderate",
        "severity_score": 0.65,
        "estimated_repair_cost": 1500,
        "repair_time_estimate": 3
    }
else:
    # Detect damage in the image
    print(f"Analyzing image: {test_image}")
    assessment = damage_detector.detect_damage(test_image)

print("\nDamage Assessment:")
print(assessment)

# Get telematics data
driver_id = "12345"
incident_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
telematics_data = telematics_processor.check_driving_behavior_near_incident(driver_id, incident_time)

print("\nTelematics Data:")
print(telematics_data)

# Check for fraud
fraud_result = fraud_detector.evaluate_claim(assessment, telematics_data, None, incident_time)
assessment["fraud_rating"] = fraud_result.get("fraud_rating")
assessment["fraud_probability"] = fraud_result.get("fraud_probability")

print("\nFraud Detection:")
print(fraud_result)

# Send Einstein GPT simulation response
print("\nSending Einstein GPT simulation to Slack...")
claim_id = f"TEST-{datetime.now().strftime('%Y%m%d%H%M')}"
result = agentforce.trigger_claim_processing_agent(claim_id, assessment, channel_id, client)

print(f"Einstein GPT simulation sent: {result}")
print("Check your Slack channel for the message!")
