"""
Main application file for the InsurTech platform.
"""
import os
import logging
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config.config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_SIGNING_SECRET
from slack.handlers.damage_assessment_handler import register_handlers as register_damage_assessment_handlers
from slack.handlers.scheduling_handler import register_handlers as register_scheduling_handlers
from slack.handlers.telematics_handler import register_handlers as register_telematics_handlers
from slack_integration.admin_handlers import AdminHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to start the application."""
    # Load environment variables
    load_dotenv()
    
    # Initialize Slack app
    app = App(
        token=SLACK_BOT_TOKEN,
        signing_secret=SLACK_SIGNING_SECRET
    )
    
    # Register handlers
    register_damage_assessment_handlers(app)
    register_scheduling_handlers(app)
    register_telematics_handlers(app)
    
    # Register the admin appointments command directly
    @app.command("/admin-appointments")
    def handle_admin_appointments_command(ack, command, client, logger):
        logger.info(f"Admin appointments command received from user {command['user_id']}")
        ack()
        
        try:
            # Import here to avoid circular imports
            from slack_integration.admin_handlers import AdminHandler
            admin_handler = AdminHandler(app)
            
            # Forward to the handler
            admin_handler.handle_admin_appointments(ack=lambda: None, command=command, client=client, logger=logger)
        except Exception as e:
            logger.error(f"Error handling admin appointments command: {e}")
            client.chat_postEphemeral(
                channel=command["channel_id"],
                user=command["user_id"],
                text="Sorry, there was an error loading the admin dashboard."
            )
    
    # Add a simple test listener
    @app.message("hello")
    def handle_hello(message, say, logger):
        logger.info(f"Received hello message from user {message['user']}")
        say(f"Hi there, <@{message['user']}>!")
    
    # Start the app
    logger.info("Starting InsurTech platform Slack app...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()

if __name__ == "__main__":
    main() 