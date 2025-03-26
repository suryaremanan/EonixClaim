"""
Fix the AI response in Slack by updating the Agentforce manager and ensuring
it's properly called in the damage assessment handler.
"""
import os
import re

# 1. First, fix the Agentforce manager to properly include text parameter
agentforce_path = "salesforce/agentforce.py"
with open(agentforce_path, "r") as f:
    content = f.read()

# Add missing text parameter
fixed_content = content.replace(
    "client.chat_postMessage(\n                channel=channel_id,\n                blocks=enhanced_response,",
    "client.chat_postMessage(\n                channel=channel_id,\n                blocks=enhanced_response,\n                text=\"AI-Enhanced Damage Analysis\","
)

# Make sure the _simulate_einstein_gpt_response method has actual content (not placeholders)
if "blocks = [\n            # ... existing blocks ...\n        ]" in content:
    fixed_content = fixed_content.replace(
        "blocks = [\n            # ... existing blocks ...\n        ]",
        """blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "AI-Enhanced Damage Analysis"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*I've analyzed the damage to your vehicle and found:*\\n\\n" +
                           f"The damage appears to be {severity.lower()} in nature, affecting " +
                           f"the {', '.join(damaged_parts)}. This type of damage typically " +
                           f"results from road debris impact or a minor collision."
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Repair Details:*\\n• Estimated cost: ${repair_cost:.2f}\\n" +
                           f"• Estimated time: {max(2, len(damaged_parts) * 1.5):.1f} days\\n" +
                           f"• Recommended service: Certified glass repair specialist"
                }
            }
        ]"""
    )

with open(agentforce_path, "w") as f:
    f.write(fixed_content)
print(f"Fixed Agentforce manager at {agentforce_path}")

# 2. Now ensure the damage assessment handler is calling the Agentforce manager
handler_path = "slack/handlers/damage_assessment_handler.py"
with open(handler_path, "r") as f:
    content = f.read()

# Make sure AgentforceManager is imported
if "from salesforce.agentforce import AgentforceManager" not in content:
    # Add import statement
    import_section = "from fraud_detection.fraud_detector import FraudDetector"
    content = content.replace(
        import_section,
        import_section + "\nfrom salesforce.agentforce import AgentforceManager"
    )

# Make sure AgentforceManager is initialized
if "agentforce_manager = AgentforceManager()" not in content:
    # Add initialization
    init_section = "fraud_detector = FraudDetector()"
    content = content.replace(
        init_section,
        init_section + "\nagentforce_manager = AgentforceManager()"
    )

# Make sure AgentforceManager is called after fraud detection
if "agentforce_manager.trigger_claim_processing_agent" not in content:
    # Find fraud detection section
    fraud_section = "assessment[\"fraud_flags\"] = fraud_result.get(\"fraud_flags\", [])"
    
    # Add call to Agentforce manager
    agentforce_call = """
                # Trigger AI-enhanced response via Agentforce
                try:
                    claim_id = f"CL-{datetime.now().strftime('%Y%m%d%H%M')}"
                    logger.info(f"Triggering Einstein GPT simulation for claim {claim_id}")
                    agentforce_manager.trigger_claim_processing_agent(
                        claim_id,
                        assessment,
                        channel_id,
                        client
                    )
                except Exception as e:
                    logger.error(f"Error triggering Einstein GPT simulation: {e}")"""
    
    content = content.replace(
        fraud_section,
        fraud_section + agentforce_call
    )

with open(handler_path, "w") as f:
    f.write(content)
print(f"Fixed damage assessment handler at {handler_path}")

# 3. Create a direct test script to verify
test_file = "test_direct_ai_response.py"
with open(test_file, "w") as f:
    f.write("""
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
""")
print(f"Created direct test script at {test_file}")

print("\nFixes applied! Now try these options:\n")
print("1. Run the direct test to verify the Einstein GPT simulation:")
print("   python test_direct_ai_response.py\n")
print("2. Or restart your main application:")
print("   python run.py\n")
print("Then upload a new image to test the full flow.") 