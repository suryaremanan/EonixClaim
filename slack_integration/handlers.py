"""
Slack event handlers module.

This module contains handler functions for various Slack events and interactions
in the InsurTech platform.
"""
import logging
import json
import re
import tempfile
import os
from typing import Dict, Any, List, Optional, Callable

from slack_sdk.web.client import WebClient

from image_processing.image_preprocessor import ImagePreprocessor
from image_processing.yolo_detector import VehicleDamageDetector
from salesforce.api_client import SalesforceClient
from salesforce.data_sync import SalesforceSync
from ml_models.fraud_detection import FraudDetector
from blockchain.ethereum_client import EthereumClient
from slack_integration.message_builder import MessageBuilder
from config.config import FRAUD_DETECTION_MESSAGE

# Configure logger
logger = logging.getLogger(__name__)

class SlackEventHandlers:
    """
    Handlers for Slack events and interactions.
    
    This class contains methods to handle various Slack events and interactions
    such as messages, button clicks, and file uploads.
    """
    
    def __init__(self, 
                 image_preprocessor: ImagePreprocessor,
                 damage_detector: VehicleDamageDetector,
                 salesforce_client: SalesforceClient,
                 salesforce_sync: SalesforceSync,
                 fraud_detector: FraudDetector,
                 ethereum_client: EthereumClient):
        """
        Initialize the Slack event handlers.
        
        Args:
            image_preprocessor: ImagePreprocessor instance
            damage_detector: VehicleDamageDetector instance
            salesforce_client: SalesforceClient instance
            salesforce_sync: SalesforceSync instance
            fraud_detector: FraudDetector instance
            ethereum_client: EthereumClient instance
        """
        self.image_preprocessor = image_preprocessor
        self.damage_detector = damage_detector
        self.salesforce_client = salesforce_client
        self.salesforce_sync = salesforce_sync
        self.fraud_detector = fraud_detector
        self.ethereum_client = ethereum_client
        self.message_builder = MessageBuilder()
        
        logger.info("Initialized SlackEventHandlers")
        
    def handle_help_command(self, client: WebClient, channel_id: str) -> None:
        """
        Handle help command.
        
        Args:
            client: Slack client
            channel_id: ID of the channel where the command was received
        """
        try:
            blocks = MessageBuilder.build_help_message()
            
            client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text="InsurTech Assistant Help"
            )
            
        except Exception as e:
            logger.error(f"Error handling help command: {e}")
            client.chat_postMessage(
                channel=channel_id,
                text="Sorry, I encountered an error displaying help information. Please try again later."
            )
            
    def handle_policy_command(self, client: WebClient, channel_id: str, policy_number: str) -> None:
        """
        Handle policy command.
        
        Args:
            client: Slack client
            channel_id: ID of the channel where the command was received
            policy_number: Policy number to look up
        """
        try:
            # Get policy from Salesforce
            policy = self.salesforce_client.get_policy(policy_number)
            
            if not policy:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"Sorry, I couldn't find policy {policy_number}. Please check the number and try again."
                )
                return
                
            # Build policy info message
            blocks = MessageBuilder.build_policy_info_message(policy)
            
            client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text=f"Policy Information for {policy_number}"
            )
            
        except Exception as e:
            logger.error(f"Error handling policy command for {policy_number}: {e}")
            client.chat_postMessage(
                channel=channel_id,
                text=f"Sorry, I encountered an error retrieving policy {policy_number}. Please try again later."
            )
            
    def handle_claim_command(self, client: WebClient, channel_id: str, claim_id: str) -> None:
        """
        Handle claim command.
        
        Args:
            client: Slack client
            channel_id: ID of the channel where the command was received
            claim_id: Claim ID to look up
        """
        try:
            # Get claim from Salesforce
            claim = self.salesforce_client.get_claim(claim_id)
            
            if not claim:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"Sorry, I couldn't find claim {claim_id}. Please check the ID and try again."
                )
                return
                
            # Build claim info message
            message = f"*Claim Status:* {claim['status']}\n"
            message += f"*Policy Number:* {claim['policy_number']}\n"
            message += f"*Date Submitted:* {claim['claim_date']}\n"
            message += f"*Estimated Amount:* ${claim['estimated_amount']:.2f}\n"
            message += f"*Description:* {claim['description']}\n"
            
            client.chat_postMessage(
                channel=channel_id,
                text=message
            )
            
        except Exception as e:
            logger.error(f"Error handling claim command for {claim_id}: {e}")
            client.chat_postMessage(
                channel=channel_id,
                text=f"Sorry, I encountered an error retrieving claim {claim_id}. Please try again later."
            )
            
    def handle_file_share(self, client: WebClient, event: Dict[str, Any]) -> None:
        """
        Handle file share event.
        
        Args:
            client: Slack client
            event: File share event data
        """
        try:
            # Get file info
            file_info = client.files_info(file=event['file_id'])['file']
            
            # Check if the file is an image
            if not file_info['mimetype'].startswith('image/'):
                client.chat_postMessage(
                    channel=event['channel_id'],
                    text="Sorry, I can only process image files for damage detection."
                )
                return
                
            # Download the file
            file_response = client.files_info(file=event['file_id'])
            file_url = file_response['file']['url_private']
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_info['name'])[1]) as temp_file:
                temp_path = temp_file.name
                
            # Download with authorization
            headers = {"Authorization": f"Bearer {client.token}"}
            response = requests.get(file_url, headers=headers)
            
            with open(temp_path, 'wb') as file:
                file.write(response.content)
                
            # Preprocess the image
            preprocessed_path = self.image_preprocessor.preprocess(temp_path)
            
            if not preprocessed_path:
                client.chat_postMessage(
                    channel=event['channel_id'],
                    text="Sorry, I couldn't process your image. Please make sure it's a clear photo of vehicle damage."
                )
                return
                
            # Detect damage
            damage_results = self.damage_detector.detect_damage(preprocessed_path)
            
            # If no damage detected
            if not damage_results['damage_summary']:
                client.chat_postMessage(
                    channel=event['channel_id'],
                    text="I couldn't detect any vehicle damage in this image. Please upload a clearer photo of the damaged area."
                )
                return
                
            # Build damage summary
            damage_summary = "*Detected Vehicle Damage:*\n\n"
            
            for damage_type, count in damage_results['damage_summary'].items():
                damage_summary += f"• {damage_type.replace('_', ' ').title()}: {count} instance(s)\n"
                
            damage_summary += f"\nSeverity Score: {damage_results['severity_score']:.2f}/1.0"
            
            # Upload the annotated image
            client.files_upload(
                channels=event['channel_id'],
                file=damage_results['image_path'],
                title="Damage Detection Results",
                initial_comment="Here's what I detected in your image:"
            )
            
            # Post damage summary with submit claim button
            blocks = MessageBuilder.build_damage_detection_message(damage_results)
            
            client.chat_postMessage(
                channel=event['channel_id'],
                blocks=blocks,
                text="Damage detected in image"
            )
            
            # Clean up temporary files
            try:
                os.remove(temp_path)
                # Don't remove the preprocessed or annotated image yet, as they might be needed for the claim process
            except Exception as e:
                logger.warning(f"Error cleaning up temporary files: {e}")
                
        except Exception as e:
            logger.error(f"Error handling file share: {e}")
            client.chat_postMessage(
                channel=event['channel_id'],
                text="Sorry, I encountered an error processing your image. Please try again later."
            ) 