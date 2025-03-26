"""
Slack application for the InsurTech platform.

This module implements a Slack bot for interaction with the InsurTech platform,
allowing users to submit claims, check policy information, and more.
"""
import os
import logging
from typing import Dict, Any
import json
import tempfile

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config.config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_SIGNING_SECRET, FRAUD_DETECTION_MESSAGE
from image_processing.yolo_detector import VehicleDamageDetector
from image_processing.image_preprocessor import ImagePreprocessor
from salesforce.api_client import SalesforceClient
from salesforce.data_sync import SalesforceSync
from ml_models.fraud_detection import FraudDetector
from blockchain.ethereum_client import EthereumClient

# Configure logger
logger = logging.getLogger(__name__)

class InsurTechSlackBot:
    """
    Slack bot for the InsurTech platform.
    
    This class implements a Slack bot that allows users to interact with
    the InsurTech platform, submit claims, and check policy information.
    """
    
    def __init__(self, bot_token: str = SLACK_BOT_TOKEN,
                 app_token: str = SLACK_APP_TOKEN,
                 signing_secret: str = SLACK_SIGNING_SECRET):
        """
        Initialize the Slack bot.
        
        Args:
            bot_token: Slack bot token
            app_token: Slack app token
            signing_secret: Slack signing secret
        """
        self.bot_token = bot_token
        self.app_token = app_token
        
        # Initialize Slack app
        self.app = App(token=bot_token, signing_secret=signing_secret)
        
        # Initialize components
        self.image_preprocessor = ImagePreprocessor()
        self.damage_detector = VehicleDamageDetector()
        self.salesforce_client = SalesforceClient()
        self.salesforce_sync = SalesforceSync(self.salesforce_client)
        self.fraud_detector = FraudDetector()
        self.ethereum_client = EthereumClient()
        
        # Register event handlers
        self._register_handlers()
        
        logger.info("Initialized InsurTech Slack Bot")
        
    def _register_handlers(self) -> None:
        """Register event handlers for Slack interactions."""
        # Message handlers
        self.app.message("help")(self._handle_help)
        self.app.message("policy")(self._handle_policy_request)
        
        # Action handlers
        self.app.action("submit_claim")(self._handle_submit_claim)
        self.app.action("confirm_claim")(self._handle_confirm_claim)
        self.app.action("cancel_claim")(self._handle_cancel_claim)
        
        # File share handler for damage images
        self.app.event("file_shared")(self._handle_file_shared)
        
        # View submission handlers
        self.app.view("claim_details_modal")(self._handle_claim_details_submission)
        
        logger.info("Registered Slack event handlers")
        
    def start(self) -> None:
        """Start the Slack bot."""
        try:
            handler = SocketModeHandler(self.app, self.app_token)
            handler.start()
            logger.info("Started InsurTech Slack Bot")
        except Exception as e:
            logger.error(f"Error starting Slack bot: {e}")
            
    def _handle_help(self, message, say) -> None:
        """
        Handle help request.
        
        Args:
            message: Message data
            say: Function to send a message
        """
        help_text = """
*InsurTech Bot Help*

You can use this bot to:
• Check your policy information
• Submit an insurance claim
• Upload vehicle damage photos
• Check claim status

*Commands:*
• `help` - Show this help message
• `policy <policy_number>` - Get policy information
• Upload a photo and say "claim" to start a claim process

*Need more help?*
Contact customer support at support@insurtech.example.com
        """
        
        say(help_text)
        
    def _handle_policy_request(self, message, say) -> None:
        """
        Handle policy information request.
        
        Args:
            message: Message data
            say: Function to send a message
        """
        # Extract policy number from message
        parts = message['text'].split()
        
        if len(parts) < 2:
            say("Please provide a policy number. Example: `policy P123456`")
            return
            
        policy_number = parts[1].strip()
        
        # Get policy from Salesforce
        policy = self.salesforce_client.get_policy(policy_number)
        
        if not policy:
            say(f"Sorry, I couldn't find policy {policy_number}. Please check the number and try again.")
            return
            
        # Format policy information
        policy_info = f"""
*Policy Information*

• *Policy Number:* {policy['policy_number']}
• *Customer:* {policy['customer_name']}
• *Vehicle VIN:* {policy['vehicle_vin']}
• *Status:* {policy['status']}
• *Premium:* ${policy['premium_amount']:.2f}
• *Coverage Period:* {policy['start_date']} to {policy['end_date']}

Need to file a claim? Upload a photo of the damage to get started.
        """
        
        say(policy_info)
        
    def _handle_file_shared(self, event, client) -> None:
        """
        Handle file shared event.
        
        Args:
            event: Event data
            client: Slack client
        """
        try:
            # Get file info
            file_info = client.files_info(file=event['file_id'])
            file_url = file_info['file']['url_private_download']
            
            # Download file to temporary location
            temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            
            headers = {'Authorization': f'Bearer {self.bot_token}'}
            response = requests.get(file_url, headers=headers)
            
            with open(temp_file.name, 'wb') as f:
                f.write(response.content)
                
            # Preprocess image
            preprocessed_image = self.image_preprocessor.preprocess(temp_file.name)
            
            if not preprocessed_image:
                client.chat_postMessage(
                    channel=event['channel_id'],
                    text="Sorry, I couldn't process that image. Please try uploading a clearer photo."
                )
                return
                
            # Detect damage
            damage_results = self.damage_detector.detect_damage(preprocessed_image)
            
            # Send message with results
            damage_types = list(damage_results['damage_summary'].keys())
            
            if not damage_types:
                client.chat_postMessage(
                    channel=event['channel_id'],
                    text="I didn't detect any damage in this image. Please try uploading a clearer photo of the damaged area."
                )
                return
                
            # Upload annotated image
            client.files_upload(
                channels=event['channel_id'],
                file=damage_results['image_path'],
                title="Detected Damage"
            )
            
            # Send damage summary
            damage_summary = f"I detected the following damage:\n"
            for damage_type, count in damage_results['damage_summary'].items():
                damage_summary += f"• {damage_type.replace('_', ' ').title()}: {count} instance(s)\n"
                
            damage_summary += f"\nSeverity Score: {damage_results['severity_score']:.2f}/1.0"
            
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": damage_summary
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Submit Claim"
                            },
                            "style": "primary",
                            "action_id": "submit_claim",
                            "value": json.dumps({"damage_results": damage_results})
                        }
                    ]
                }
            ]
            
            client.chat_postMessage(
                channel=event['channel_id'],
                blocks=blocks,
                text="Damage detected in image"
            )
            
        except Exception as e:
            logger.error(f"Error handling file share: {e}")
            client.chat_postMessage(
                channel=event['channel_id'],
                text="Sorry, I encountered an error processing your image. Please try again later."
            )
            
    def _handle_submit_claim(self, ack, body, client) -> None:
        """
        Handle submit claim button click.
        
        Args:
            ack: Function to acknowledge the request
            body: Request body
            client: Slack client
        """
        # Acknowledge the button click
        ack()
        
        try:
            # Extract damage results
            payload = json.loads(body['actions'][0]['value'])
            damage_results = payload['damage_results']
            
            # Open claim details modal
            client.views_open(
                trigger_id=body['trigger_id'],
                view={
                    "type": "modal",
                    "callback_id": "claim_details_modal",
                    "private_metadata": json.dumps({"damage_results": damage_results}),
                    "title": {
                        "type": "plain_text",
                        "text": "Submit Insurance Claim"
                    },
                    "submit": {
                        "type": "plain_text",
                        "text": "Submit"
                    },
                    "close": {
                        "type": "plain_text",
                        "text": "Cancel"
                    },
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "Please provide the details for your claim."
                            }
                        },
                        {
                            "type": "input",
                            "block_id": "policy_number",
                            "label": {
                                "type": "plain_text",
                                "text": "Policy Number"
                            },
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "policy_input"
                            }
                        },
                        {
                            "type": "input",
                            "block_id": "description",
                            "label": {
                                "type": "plain_text",
                                "text": "Description of Incident"
                            },
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "description_input",
                                "multiline": True
                            }
                        },
                        {
                            "type": "input",
                            "block_id": "incident_date",
                            "label": {
                                "type": "plain_text",
                                "text": "Incident Date"
                            },
                            "element": {
                                "type": "datepicker",
                                "action_id": "date_input"
                            }
                        }
                    ]
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling submit claim: {e}")
            client.chat_postMessage(
                channel=body['user']['id'],
                text="Sorry, I encountered an error processing your claim. Please try again later."
            )
            
    def _handle_claim_details_submission(self, ack, view, client, body) -> None:
        """
        Handle claim details modal submission.
        
        Args:
            ack: Function to acknowledge the request
            view: View data
            client: Slack client
            body: Request body
        """
        # Acknowledge the submission
        ack()
        
        try:
            # Extract private metadata
            metadata = json.loads(view['private_metadata'])
            damage_results = metadata['damage_results']
            
            # Extract form values
            policy_number = view['state']['values']['policy_number']['policy_input']['value']
            description = view['state']['values']['description']['description_input']['value']
            incident_date = view['state']['values']['incident_date']['date_input']['selected_date']
            
            # Get policy from Salesforce
            policy = self.salesforce_client.get_policy(policy_number)
            
            if not policy:
                client.chat_postMessage(
                    channel=body['user']['id'],
                    text=f"Sorry, I couldn't find policy {policy_number}. Please check the number and try again."
                )
                return
                
            # Prepare claim data
            claim_data = {
                'policy_id': policy['id'],
                'claim_date': incident_date,
                'description': description,
                'damage_type': ', '.join(damage_results['damage_summary'].keys()),
                'estimated_amount': 500.0 * damage_results['severity_score'],
                'damage_images': [damage_results['image_path']]
            }
            
            # Run fraud detection
            fraud_result = self.fraud_detector.detect_fraud(claim_data)
            
            # If potentially fraudulent, handle specially
            if fraud_result['is_fraudulent']:
                message = FRAUD_DETECTION_MESSAGE.format(claim_id=f"F{int(time.time())}")
                
                client.chat_postMessage(
                    channel=body['user']['id'],
                    text=message
                )
                return
                
            # Create claim in Salesforce
            claim_id = self.salesforce_sync.sync_damage_assessment(policy_number, damage_results)
            
            if not claim_id:
                client.chat_postMessage(
                    channel=body['user']['id'],
                    text="Sorry, there was an error submitting your claim. Please try again later."
                )
                return
                
            # Record claim on blockchain
            blockchain_recorded = self.ethereum_client.record_claim(
                claim_id, 
                policy_number, 
                {
                    'damage_types': list(damage_results['damage_summary'].keys()),
                    'severity_score': damage_results['severity_score'],
                    'description': description,
                    'incident_date': incident_date
                }
            )
            
            # Send confirmation message
            confirmation = f"""
*Claim Submitted Successfully*

• *Claim ID:* {claim_id}
• *Policy Number:* {policy_number}
• *Incident Date:* {incident_date}
• *Damage Types:* {', '.join(damage_types).replace('_', ' ').title()}
• *Estimated Damage:* ${claim_data['estimated_amount']:.2f}

You'll receive updates as your claim is processed. You can check the status anytime by asking about your claim ID.
            """
            
            if blockchain_recorded:
                confirmation += "\n\n_Your claim has been securely recorded on blockchain for immutable record-keeping._"
                
            client.chat_postMessage(
                channel=body['user']['id'],
                text=confirmation
            )
            
        except Exception as e:
            logger.error(f"Error handling claim submission: {e}")
            client.chat_postMessage(
                channel=body['user']['id'],
                text="Sorry, I encountered an error processing your claim. Please try again later."
            )
            
    def _handle_confirm_claim(self, ack, body, client) -> None:
        """
        Handle claim confirmation.
        
        Args:
            ack: Function to acknowledge the request
            body: Request body
            client: Slack client
        """
        # Acknowledge the button click
        ack()
        
        try:
            # Extract claim data
            payload = json.loads(body['actions'][0]['value'])
            claim_id = payload['claim_id']
            
            # Update claim status in Salesforce
            updated = self.salesforce_client.update_claim_status(
                claim_id, 
                "Processing",
                "Claim confirmed by customer via Slack"
            )
            
            if updated:
                client.chat_postMessage(
                    channel=body['channel']['id'],
                    text=f"Thank you for confirming your claim. Your claim (ID: {claim_id}) is now being processed. We'll update you on the progress."
                )
            else:
                client.chat_postMessage(
                    channel=body['channel']['id'],
                    text=f"There was an issue updating your claim status. Please contact customer support for assistance."
                )
                
        except Exception as e:
            logger.error(f"Error handling claim confirmation: {e}")
            client.chat_postMessage(
                channel=body['channel']['id'],
                text="Sorry, I encountered an error processing your confirmation. Please try again later."
            )
            
    def _handle_cancel_claim(self, ack, body, client) -> None:
        """
        Handle claim cancellation.
        
        Args:
            ack: Function to acknowledge the request
            body: Request body
            client: Slack client
        """
        # Acknowledge the button click
        ack()
        
        try:
            # Extract claim data
            payload = json.loads(body['actions'][0]['value'])
            claim_id = payload['claim_id']
            
            # Update claim status in Salesforce
            updated = self.salesforce_client.update_claim_status(
                claim_id, 
                "Cancelled",
                "Claim cancelled by customer via Slack"
            )
            
            if updated:
                client.chat_postMessage(
                    channel=body['channel']['id'],
                    text=f"Your claim (ID: {claim_id}) has been cancelled. If this was a mistake, please contact customer support."
                )
            else:
                client.chat_postMessage(
                    channel=body['channel']['id'],
                    text=f"There was an issue cancelling your claim. Please contact customer support for assistance."
                )
                
        except Exception as e:
            logger.error(f"Error handling claim cancellation: {e}")
            client.chat_postMessage(
                channel=body['channel']['id'],
                text="Sorry, I encountered an error processing your cancellation. Please try again later."
            ) 