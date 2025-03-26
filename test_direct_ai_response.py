
import os
import sys
import logging
from dotenv import load_dotenv
from slack_sdk import WebClient

# Set up path and load environment variables
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our module
from salesforce.agentforce import AgentforceManager

# Initialize the Slack client and Agentforce manager
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
agentforce = AgentforceManager()

# Set up test data
channel_id = "C08HJ6LA9MM"  # Your channel ID
claim_id = "TEST-DIRECT-12345"
assessment = {
    "damaged_parts": ["windshield"],
    "severity": "Moderate",
    "severity_score": 0.65,
    "estimated_repair_cost": 800.00,
    "fraud_probability": 0.1,
    "fraud_rating": "Low"
}

# Call the method directly
print(f"Sending direct AI response to channel {channel_id}...")
result = agentforce.trigger_claim_processing_agent(
    claim_id,
    assessment,
    channel_id,
    client
)

print(f"Result: {result}")
print("Check your Slack channel for the message!")
