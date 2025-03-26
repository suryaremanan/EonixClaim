import os
import sys
import json
from slack_sdk import WebClient
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

# Initialize Slack client
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
channel_id = "C08HJ6LA9MM"  # Your channel ID

# Create a sample damage report similar to what your YOLO detector would produce
damage_report = {
    "status": "success",
    "damaged_parts": ["windshield", "front bumper"],
    "damages": ["crack", "scratch"],
    "severity": "Moderate",
    "estimated_repair_cost": 1200.50,
    "repair_time_estimate": "3.5 days"
}

# Send a formatted message to Slack
blocks = [
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
            "text": f"*I've analyzed the damage to your vehicle and found:*\n\n" +
                   f"The damage appears to be {damage_report['severity'].lower()} in nature, affecting " +
                   f"the {', '.join(damage_report['damaged_parts'])}. This type of damage typically " +
                   f"results from road debris impact or a minor collision."
        }
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Repair Details:*\n• Estimated cost: ${damage_report['estimated_repair_cost']:.2f}\n" +
                   f"• Estimated time: {damage_report['repair_time_estimate']}\n" +
                   f"• Recommended service: Certified glass repair specialist"
        }
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*Next Steps:*\n" +
                    "1. We'll review your claim within 24 hours\n" +
                    "2. A claims adjuster will contact you to confirm details\n" +
                    "3. You can schedule repairs at your convenience using the button below"
        }
    },
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Schedule Repair"
                },
                "style": "primary",
                "value": "schedule_repair_12345",
                "action_id": "schedule_repair"
            }
        ]
    }
]

# Send the message
response = client.chat_postMessage(
    channel=channel_id,
    blocks=blocks,
    text="AI-Enhanced Damage Analysis"  # Including text to avoid the warning
)

print(f"Message sent: {response['ts']}") 