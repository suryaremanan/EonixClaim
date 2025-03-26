"""
Configuration module for the InsurTech platform.

This module loads environment variables and provides a centralized
configuration for all components of the platform.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Paths and general settings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(BASE_DIR, 'tmp')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# Ensure directories exist
for directory in [TEMP_DIR, LOG_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# YOLO Model Configuration
YOLO_MODEL_PATH = os.getenv('YOLO_MODEL_PATH')
YOLO_CONFIDENCE_THRESHOLD = float(os.getenv('YOLO_CONFIDENCE_THRESHOLD', '0.15'))

# Updated vehicle part classes from the labeling system - proper case matching
VEHICLE_PART_CLASSES = []

# Damage types - expanded and proper case matching
DAMAGE_CLASSES = [
    'damaged door',
    'damaged window',
    'damaged headlight',
    'damaged mirror',
    'dent',
    'damaged hood', 
    'damaged bumper',
    'damaged wind shield'
]

# Telematics Configuration
TELEMATICS_DATA_PATH = os.getenv('TELEMATICS_DATA_PATH', 'data/telematics')
RISK_THRESHOLD_HIGH = float(os.getenv('RISK_THRESHOLD_HIGH', '0.75'))
RISK_THRESHOLD_MEDIUM = float(os.getenv('RISK_THRESHOLD_MEDIUM', '0.5'))

# Telematics Thresholds
ACCELERATION_THRESHOLD = float(os.getenv('ACCELERATION_THRESHOLD', '2.5'))  # m/s² (harsh acceleration)
BRAKING_THRESHOLD = float(os.getenv('BRAKING_THRESHOLD', '-2.5'))  # m/s² (harsh braking)
CORNERING_THRESHOLD = float(os.getenv('CORNERING_THRESHOLD', '1.8'))  # lateral g-force (harsh cornering)
SPEEDING_THRESHOLD = float(os.getenv('SPEEDING_THRESHOLD', '90'))  # km/h (speeding)

# Salesforce Configuration
SF_USERNAME = os.getenv('SF_USERNAME')
SF_PASSWORD = os.getenv('SF_PASSWORD')
SF_SECURITY_TOKEN = os.getenv('SF_SECURITY_TOKEN')
SF_DOMAIN = os.getenv('SF_DOMAIN', 'login')
SF_INSTANCE_URL = os.getenv('SF_INSTANCE_URL')

# ML Model Configuration
FRAUD_MODEL_PATH = os.getenv('FRAUD_MODEL_PATH', '/home/suryaremanan/eonixclaim/models/fraud_detection.pkl')
MAINTENANCE_MODEL_PATH = os.getenv('MAINTENANCE_MODEL_PATH', 'models/predictive_maintenance.pkl')

# Blockchain Configuration
ETHEREUM_PROVIDER_URL = os.getenv('ETHEREUM_PROVIDER_URL', 'http://localhost:8545')
ETHEREUM_PRIVATE_KEY = os.getenv('ETHEREUM_PRIVATE_KEY')
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')

# Slack Configuration
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET')
SLACK_APP_TOKEN = os.getenv('SLACK_APP_TOKEN')

# Response templates for specific scenarios
FRAUD_DETECTION_MESSAGE = (
    "⚠️ *POTENTIAL FRAUD DETECTED* ⚠️\n"
    "Our system has identified potential irregularities with this claim. "
    "The case has been escalated to our fraud investigation team. "
    "Reference #: {claim_id}"
)

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO') 