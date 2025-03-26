"""
Authentication utilities for Slack in the Eonix insurance platform.
"""
import os
import logging
from typing import List

# Configure logger
logger = logging.getLogger(__name__)

def is_admin_user(user_id: str) -> bool:
    """
    Check if a user is an admin.
    
    Args:
        user_id: Slack user ID
        
    Returns:
        True if the user is an admin, False otherwise
    """
    # Get admin user IDs from environment variable
    admin_users = os.environ.get("ADMIN_USERS", "").split(",")
    admin_user_ids = os.environ.get("ADMIN_USER_IDS", "").split(",")
    
    # Combine both environment variables
    all_admins = admin_users + admin_user_ids
    
    # Clean up the list (remove empty strings, strip whitespace)
    all_admins = [admin.strip() for admin in all_admins if admin.strip()]
    
    logger.info(f"Checking if {user_id} is in admin list: {all_admins}")
    
    return user_id in all_admins 