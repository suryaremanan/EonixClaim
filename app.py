"""
Main application for the InsurTech platform.

This module initializes and runs the InsurTech platform, setting up the
Slack interface and other components.
"""
import logging
import os
import sys
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config.config import SLACK_APP_TOKEN, LOG_LEVEL, LOG_DIR
from slack_integration.app import InsurTechSlackBot
from utils.logging_config import setup_logging

# Set up logging
setup_logging(LOG_DIR, LOG_LEVEL)
logger = logging.getLogger(__name__)

def main():
    """Initialize and run the InsurTech platform."""
    try:
        logger.info("Starting InsurTech platform")
        
        # Initialize the Slack bot
        slack_bot = InsurTechSlackBot()
        
        # Start the Socket Mode handler
        if not SLACK_APP_TOKEN:
            logger.error("SLACK_APP_TOKEN not set in environment variables")
            sys.exit(1)
            
        handler = SocketModeHandler(slack_bot.app, SLACK_APP_TOKEN)
        
        logger.info("InsurTech platform initialized, starting Socket Mode handler")
        handler.start()
        
    except Exception as e:
        logger.critical(f"Fatal error starting InsurTech platform: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 