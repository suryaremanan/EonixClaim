"""
Logging configuration for the InsurTech platform.

This module provides utilities for setting up logging across the
InsurTech platform.
"""
import logging
import logging.handlers
import os
from datetime import datetime

def setup_logging(log_dir: str, log_level: str = "INFO") -> None:
    """
    Set up logging for the InsurTech platform.
    
    Args:
        log_dir: Directory to store log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create log directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # Determine log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
        
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Log format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (rotating)
    log_file = os.path.join(log_dir, f"insurtech_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10485760, backupCount=5
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Log startup message
    root_logger.info(f"Logging initialized at level {log_level}") 