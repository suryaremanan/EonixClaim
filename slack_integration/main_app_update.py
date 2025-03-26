"""
Main Slack application integration for the Eonix insurance platform.
Coordinates between all platform components.
"""
import os
import logging
import sys
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import components
from slack_integration.admin_integration import register_admin_handlers
from slack_integration.image_handlers import ImageHandler
from integrations.claim_processor import ClaimProcessor
from image_processing.vehicle_parts_detector import VehicleDamageDetector
from fraud_detection.fraud_detector import FraudDetector
from telematics.telematics_processor import TelematicsProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Slack app
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Initialize components
claim_processor = ClaimProcessor()
damage_detector = VehicleDamageDetector()
fraud_detector = FraudDetector()
telematics_processor = TelematicsProcessor()

# Register image handlers
image_handler = ImageHandler(app)

# Register admin handlers
admin_bot = register_admin_handlers(app)

@app.event("app_mention")
def handle_app_mention(body, say, logger):
    """Handle app mentions in channels."""
    text = body["event"]["text"].lower()
    
    if "help" in text:
        say("""*Eonix Insurance Platform Help*
• Upload a photo of vehicle damage to start a claim
• Type `schedule repair` to schedule a service appointment
• Type `check claim <claim_id>` to check claim status
• Admin users can use `/admin-query` for advanced queries

For more help, contact support@eonixinsurance.com""")
    elif "hello" in text or "hi" in text:
        say(f"Hello <@{body['event']['user']}>! How can I help with your insurance needs today?")
    else:
        say("I'm here to help with your insurance needs. Try uploading a photo of vehicle damage to start a claim.")

def start_app():
    """Start the Slack application."""
    try:
        # Start the Socket Mode handler
        handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
        logger.info("Starting Eonix Insurance Platform Slack app...")
        handler.start()
    except Exception as e:
        logger.error(f"Error starting app: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_app() 