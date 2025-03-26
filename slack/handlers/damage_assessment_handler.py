"""
Slack handler for vehicle damage assessment.
"""
import os
import logging
import time
from slack_bolt import App
from slack_sdk.errors import SlackApiError
from image_processing.vehicle_parts_detector import VehicleDamageDetector
from slack_sdk.web import WebClient
from telematics.telematics_processor import TelematicsProcessor
from fraud_detection.fraud_detector import FraudDetector
from salesforce.agentforce import AgentforceManager
from datetime import datetime
from config.config import FRAUD_DETECTION_MESSAGE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize vehicle damage detector
damage_detector = VehicleDamageDetector()

# Initialize the processors
telematics_processor = TelematicsProcessor()
fraud_detector = FraudDetector()
agentforce_manager = AgentforceManager()


def map_slack_to_driver_id(slack_user_id):
    
    # In a real system, this would query a database
    # For demo, we'll use a hardcoded mapping
    mapping = {
        # Add your actual Slack user ID here
        "U07R1MDV0TD": "12345"
    }
    return mapping.get(slack_user_id, "12345")  # Default to 12345 if not found


# Track processed files to prevent duplicates
processed_files = {}
PROCESSING_TIMEOUT = 60  # seconds

def register_handlers(app: App):
    """Register damage assessment handlers with the Slack app."""
    
    def process_file(file_id, channel_id, client, logger, user_id="12345"):
        """
        Process a file, with duplicate prevention.
        Returns True if file was processed, False if it was a duplicate.
        """
        # Check if file was recently processed
        current_time = time.time()
        if file_id in processed_files:
            # If the file was processed less than PROCESSING_TIMEOUT seconds ago, skip it
            if current_time - processed_files[file_id] < PROCESSING_TIMEOUT:
                logger.info(f"Skipping duplicate processing of file {file_id}")
                return False
                
        # Mark this file as processed
        processed_files[file_id] = current_time
        
        # Clean up old entries from processed_files dict
        for old_file_id in list(processed_files.keys()):
            if current_time - processed_files[old_file_id] > PROCESSING_TIMEOUT:
                del processed_files[old_file_id]
        
        # The rest of your file processing logic goes here
        try:
            # Get file info
            logger.info(f"Processing file ID: {file_id}")
            
            file_info = client.files_info(file=file_id)
            logger.info(f"File info retrieved: {file_info.get('file', {}).get('name')}")
            
            # Check if it's an image
            if not file_info["file"]["mimetype"].startswith("image/"):
                client.chat_postMessage(
                    channel=channel_id,
                    text="Please upload an image file for vehicle damage assessment."
                )
                return True
            
            # Download the file
            file_url = file_info["file"]["url_private_download"]
            download_path = f"temp/{file_id}_{file_info['file']['name']}"
            
            os.makedirs("temp", exist_ok=True)
            
            # Use requests to download the file with authorization
            import requests
            headers = {"Authorization": f"Bearer {client.token}"}
            response = requests.get(file_url, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Failed to download file: {response.status_code}")
            
            with open(download_path, "wb") as f:
                f.write(response.content)
            
            if not os.path.exists(download_path):
                raise Exception("Failed to save the downloaded file")
            
            # Process the image
            client.chat_postMessage(
                channel=channel_id,
                text="Analyzing vehicle damage... This may take a moment."
            )
            
            # Get damage assessment
            assessment = damage_detector.get_damage_assessment(download_path)
            
            if "error" in assessment:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"Error during analysis: {assessment['error']}"
                )
                return True
            
            # Add fraud detection if we have a valid assessment
            if "error" not in assessment and assessment["damaged_parts"]:
                # Use the passed user_id parameter
                driver_id = map_slack_to_driver_id(user_id)
                incident_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Get telematics data
                telematics_data = telematics_processor.check_driving_behavior_near_incident(
                    driver_id, incident_time
                )
                
                # Get fraud assessment
                fraud_result = fraud_detector.evaluate_claim(
                    assessment, telematics_data, None, incident_time
                )
                
                # Add fraud info to the assessment
                assessment["fraud_rating"] = fraud_result.get("fraud_rating")
                assessment["fraud_probability"] = fraud_result.get("fraud_probability")
                assessment["fraud_flags"] = fraud_result.get("fraud_flags", [])
                # Trigger AI-enhanced response via Agentforce
                try:
                    claim_id = f"CL-{datetime.now().strftime('%Y%m%d%H%M')}"
                    logger.info(f"Triggering Einstein GPT simulation for claim {claim_id}")
                    agentforce_manager.trigger_claim_processing_agent(
                        claim_id,
                        assessment,
                        channel_id,
                        client
                    )
                except Exception as e:
                    logger.error(f"Error triggering Einstein GPT simulation: {e}")
                
                # Add a special section for high fraud probability
                if fraud_result.get("fraud_rating") == "High":
                    # Use the pre-defined message template
                    fraud_message = FRAUD_DETECTION_MESSAGE.format(
                        claim_id="CL-" + datetime.now().strftime("%Y%m%d%H%M")
                    )
                    assessment["fraud_message"] = fraud_message
            
            # Format response message
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Vehicle Damage Assessment: {assessment['severity']} Damage"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Estimated Cost:* ${assessment['estimated_repair_cost']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Repair Time:* {assessment['repair_time_estimate']}"
                        }
                    ]
                }
            ]
            
            # Add parts detected section
            if assessment["vehicle_parts"]:
                parts_text = "*Vehicle Parts Detected:*\n" + "\n".join(f"• {part}" for part in assessment["vehicle_parts"])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": parts_text
                    }
                })
            
            # Add damage types section
            if assessment["damages"]:
                damage_text = "*Damage Types Detected:*\n" + "\n".join(f"• {damage}" for damage in assessment["damages"])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": damage_text
                    }
                })
            
            # Add damaged parts section if any
            if assessment["damaged_parts"]:
                damaged_parts_text = "*Damaged Parts:*\n" + "\n".join(f"• {part}" for part in assessment["damaged_parts"])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": damaged_parts_text
                    }
                })
                
                # Add a button to schedule repair if damage is detected
                blocks.append({
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "📅 Schedule Repair",
                                "emoji": True
                            },
                            "style": "primary",
                            "value": "claim_12345",  # This would be the actual claim ID from Salesforce
                            "action_id": "schedule_repair"
                        }
                    ]
                })
            else:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*No damage detected*"
                    }
                })
            
            # Upload annotated image
            if "annotated_image" in assessment and os.path.exists(assessment["annotated_image"]):
                try:
                    # Create a new WebClient to avoid conflicting parameters
                    from slack_sdk import WebClient as SlackWebClient
                    upload_client = SlackWebClient(token=client.token)
                    
                    # Use channels (plural) parameter instead of channel_id
                    upload_client.files_upload_v2(
                        file=open(assessment["annotated_image"], "rb"),
                        filename=os.path.basename(assessment["annotated_image"]),
                        initial_comment="Vehicle damage annotated:",
                        title="Annotated Vehicle Damage Assessment",
                        channels=[channel_id]  # Use channels as a list
                    )
                except Exception as e:
                    logger.error(f"Error uploading annotated image: {e}")
                    # Fallback to just text
                    client.chat_postMessage(
                        channel=channel_id,
                        text=f"Vehicle damage annotated: See the annotated image at {assessment['annotated_image']}"
                    )
            
            # Add fraud section to message blocks
            if "fraud_rating" in assessment:
                fraud_rating = assessment["fraud_rating"]
                fraud_prob = assessment["fraud_probability"]
                
                # Choose emoji based on fraud rating
                if fraud_rating == "High":
                    fraud_emoji = "⚠️"
                elif fraud_rating == "Medium":
                    fraud_emoji = "⚠"
                else:
                    fraud_emoji = "✅"
                    
                # Add fraud section to message blocks
                blocks.append({
                    "type": "divider"
                })
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{fraud_emoji} *Fraud Assessment:* {fraud_rating} Risk ({fraud_prob * 100:.0f}%)"
                    }
                })
                
                # For high fraud probability, show the special message
                if fraud_rating == "High" and "fraud_message" in assessment:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": assessment["fraud_message"]
                        }
                    })
            
            # Send assessment message
            client.chat_postMessage(
                channel=channel_id,
                blocks=blocks
            )
            
            # Cleanup temp file
            try:
                if os.path.exists(download_path):
                    os.remove(download_path)
                if "annotated_image" in assessment and assessment["annotated_image"] != download_path and os.path.exists(assessment["annotated_image"]):
                    os.remove(assessment["annotated_image"])
            except Exception as e:
                logger.warning(f"Failed to clean up temporary files: {e}")
            
            return True
            
        except SlackApiError as e:
            logger.error(f"Error posting message: {e}")
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            client.chat_postMessage(
                channel=channel_id,
                text=f"An error occurred during processing: {str(e)}"
            )
            
        return True
    
    @app.event("file_shared")
    def handle_file_shared(event, client, logger):
        """Handle file shared in Slack for damage assessment."""
        logger.info(f"File shared event received: {event}")
        
        # Ensure channel_id exists
        if "channel_id" not in event or not event["channel_id"]:
            logger.error("No channel_id in event payload")
            # Try to find channel_id in other fields
            if "channel" in event:
                event["channel_id"] = event["channel"]
            else:
                # Use a default channel if none is found
                event["channel_id"] = "C08HJ6LA9MM"  # Your default channel
                logger.warning(f"Using default channel_id: {event['channel_id']}")
        
        logger.info(f"Channel ID: {event.get('channel_id')}")
        
        # Add this to test if your app can post to the channel
        try:
            client.chat_postMessage(
                channel=event.get('channel_id', 'C08HXVNPNLJ'),  # Use your actual channel ID as fallback
                text="I detected a file upload event!"
            )
        except Exception as e:
            logger.error(f"Error posting test message: {e}")
        
        # Process the file with deduplication
        file_id = event.get("file_id")
        if file_id:
            user_id = event.get("user_id", "12345")
            process_file(file_id, event.get("channel_id"), client, logger, user_id)
        else:
            logger.error("No file_id in event payload")

    # Comment out or remove the file_created handler which causes duplicates
    # @app.event("file_created")
    # def handle_file_created(event, client, logger):
    #    ...
        
    # Add a message handler to test basic functionality
    @app.message("test")
    def handle_message(message, say, logger):
        logger.info(f"Message received: {message}")
        say("I'm working! Try uploading an image.")

    @app.event("message")
    def handle_message_events(body, logger, client):
        logger.info(f"Message event received: {body}")
        
        # Check if it's a file share message
        event = body.get("event", {})
        if event.get("subtype") == "file_share":
            logger.info("File share message detected")
            
            # Extract file info from the message
            files = event.get("files", [])
            if files and len(files) > 0:
                file_id = files[0].get("id")
                if file_id:
                    # Use the shared process_file function
                    try:
                        user_id = event.get("user", "12345")
                        process_file(file_id, event.get("channel"), client, logger, user_id)
                    except Exception as e:
                        logger.error(f"Error processing image: {e}")
                        # Send error message to the channel
                        try:
                            client.chat_postMessage(
                                channel=event.get("channel"),
                                text=f"Sorry, there was an error processing your image: {str(e)}"
                            )
                        except Exception as msg_error:
                            logger.error(f"Error sending error message: {msg_error}") 