"""
Admin bot integration for the Eonix insurance platform.
Registers admin commands and handlers with the main Slack application.
"""
import os
import logging
from slack_bolt import App

from admin.admin_bot import AdminBot
from database.customer_db import CustomerDatabase

# Configure logger
logger = logging.getLogger(__name__)

def register_admin_handlers(app: App):
    """
    Register admin handlers with the Slack app.
    
    Args:
        app: Slack Bolt App instance
    """
    # Initialize admin bot
    admin_bot = AdminBot(app)
    
    logger.info("Admin handlers registered with Slack app")
    
    return admin_bot 