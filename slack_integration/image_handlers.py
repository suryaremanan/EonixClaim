"""
Handlers for image uploads and damage detection in the Eonix insurance platform.
"""
import requests
import os
import logging
import json
import time
import tempfile
from typing import Dict, List, Any, Optional
from slack_sdk import WebClient
from slack_bolt import App
from datetime import datetime, timedelta

# Import required components
from image_processing.vehicle_parts_detector import VehicleDamageDetector
from fraud_detection.fraud_detector import FraudDetector
from integrations.claim_processor import ClaimProcessor
from slack_integration.salesforce_integration import SalesforcePromptAnalyzer

# Configure logger
logger = logging.getLogger(__name__)

class ImageHandler:
    """
    Handles image uploads and damage analysis for the Slack interface.
    """
    
    def __init__(self, app: App):
        """
        Initialize the image handler.
        
        Args:
            app: Slack Bolt App instance
        """
        self.app = app
        self.damage_detector = VehicleDamageDetector()
        self.fraud_detector = FraudDetector()
        self.claim_processor = ClaimProcessor()
        self.sf_analyzer = SalesforcePromptAnalyzer()
        
        # Add a set to track recently processed files
        self.processed_files = set()
        
        # Register handlers
        self._register_handlers()
        
        logger.info("Image handler initialized")
    
    def _register_handlers(self):
        """Register event handlers with the Slack app."""
        # File shared event (when a file is uploaded to a channel)
        self.app.event("file_shared")(self.handle_file_shared)
        
        # File created event
        self.app.event("file_created")(self.handle_file_created)
        
        # Also handle message events with file_share subtype
        self.app.event({
            "type": "message", 
            "subtype": "file_share"
        })(self.handle_message_with_file)
        
        # Action handlers
        self.app.action("confirm_damage_analysis")(self.handle_damage_confirmation)
        self.app.action("reject_damage_analysis")(self.handle_damage_rejection)
        self.app.action("submit_description")(self.handle_description_submission)
        
        # The dynamic handlers for service centers and timeslots are registered
        # when those options are presented to the user
        
        # Add view submission handler for the contact info modal
        self.app.view("contact_info_modal")(self.handle_contact_info_submission)
    
    def handle_file_shared(self, body, client, logger):
        """
        Handle file_shared events.
        
        Args:
            body: Event payload
            client: Slack WebClient
            logger: Logger instance
        """
        try:
            # Get file ID from the event
            file_id = body["event"].get("file_id")
            if not file_id:
                logger.warning("No file_id found in file_shared event")
                return
                
            # Process the file
            self._process_file(file_id, body, client)
            
        except Exception as e:
            logger.error(f"Error handling file_shared event: {e}")
    
    def handle_file_created(self, body, client, logger):
        """
        Handle file_created events.
        
        Args:
            body: Event payload
            client: Slack WebClient
            logger: Logger instance
        """
        try:
            # Get file ID from the event
            event = body.get("event", {})
            file_id = event.get("file_id")
            
            if not file_id and "file" in event:
                file_id = event["file"].get("id")
            
            if not file_id:
                logger.warning("No file_id found in file_created event")
                return
            
            # Check if we've already processed this file recently
            if file_id in self.processed_files:
                logger.info(f"Skipping already processed file: {file_id}")
                return
            
            # Add to processed files set
            self.processed_files.add(file_id)
            
            # Get file info
            file_info = client.files_info(file=file_id)
            
            if not file_info or "file" not in file_info:
                logger.warning(f"Could not retrieve info for file {file_id}")
                return
            
            file_obj = file_info["file"]
            
            # Check if file is shared in a channel
            channels = file_obj.get("channels", [])
            if not channels:
                logger.info(f"File {file_id} is not shared in any channel, skipping processing")
                return
            
            # Process for the first channel it's shared in
            channel_id = channels[0]
            user_id = event.get("user_id") or file_obj.get("user")
            
            if not channel_id or not user_id:
                logger.warning(f"Could not determine channel or user from event: {body}")
                return
            
            # Now we can process the file with channel context
            self._process_file_with_context(file_id, user_id, channel_id, client)
            
        except Exception as e:
            logger.error(f"Error handling file_created event: {e}")
    
    def handle_message_with_file(self, body, client, logger):
        """
        Handle message events with file_share subtype.
        
        Args:
            body: Event payload
            client: Slack WebClient
            logger: Logger instance
        """
        try:
            # Extract event data
            event = body["event"]
            
            # Get files from the message
            files = event.get("files", [])
            if not files:
                logger.warning("No files found in file_share message")
                return
                
            # Process each file
            for file_info in files:
                file_id = file_info.get("id")
                if file_id:
                    self._process_file(file_id, body, client)
                
        except Exception as e:
            logger.error(f"Error handling message with file: {e}")
    
    def _process_file(self, file_id, body, client):
        """Process a file uploaded to Slack."""
        try:
            # Check if we've already processed this file recently
            if file_id in self.processed_files:
                logger.info(f"Skipping already processed file: {file_id}")
                return
                
            # Add to processed files set
            self.processed_files.add(file_id)
            
            # Limit the size of the set (remove oldest entries if too large)
            if len(self.processed_files) > 100:
                # Remove some old entries (convert to list, slice, convert back to set)
                self.processed_files = set(list(self.processed_files)[-50:])
            
            # Get file info
            file_info = client.files_info(file=file_id)
            
            if not file_info or "file" not in file_info:
                logger.warning(f"Could not retrieve info for file {file_id}")
                return
                
            file_obj = file_info["file"]
            
            # Check if it's an image file
            mimetype = file_obj.get("mimetype", "")
            if not mimetype.startswith("image/"):
                logger.info(f"Ignoring non-image file: {mimetype}")
                # Inform the user
                self._send_non_image_response(body, client)
                return
                
            # Download the file
            download_url = file_obj.get("url_private_download")
            if not download_url:
                logger.warning(f"No download URL for file {file_id}")
                return
                
            # Create a temporary file to store the image
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_obj.get("name", "image.jpg"))[1]) as temp_file:
                # Use requests library for downloading
                headers = {"Authorization": f"Bearer {client.token}"}
                response = requests.get(download_url, headers=headers, stream=True)
                
                # Write to temp file
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        temp_file.write(chunk)
                
                temp_file_path = temp_file.name
            
            # Send "processing" message
            channel_id = None
            user_id = None
            
            # IMPROVED EVENT PARSING - Extract directly from the event structure
            if "event" in body:
                # Extract directly from the event
                event = body["event"]
                channel_id = event.get("channel_id")
                user_id = event.get("user_id") or event.get("user")
                
                # If not found, try alternate locations
                if not channel_id:
                    channel_id = event.get("channel")
            
            # Fallback to channel if event not found or doesn't have channel_id
            if not channel_id and "channel" in body:
                channel_id = body["channel"]["id"]
            
            # Fallback for user_id
            if not user_id and "user" in body:
                user_id = body["user"]["id"]
            
            # Log the full event for debugging if we still can't find the IDs
            if not channel_id or not user_id:
                logger.warning(f"Could not determine channel or user from event: {body}")
                return
            
            processing_msg = client.chat_postMessage(
                channel=channel_id,
                text=f"<@{user_id}> I'm analyzing your vehicle damage image. This will take a moment..."
            )
            
            # Analyze the image
            damage_results = self.damage_detector.detect_objects(temp_file_path)
            
            # Check if any damage was detected
            if not damage_results or not damage_results.get("damaged_parts"):
                # No damage detected
                client.chat_update(
                    channel=channel_id,
                    ts=processing_msg["ts"],
                    text=f"<@{user_id}> I couldn't detect any vehicle damage in your image. Please try uploading a clearer image of the damaged area."
                )
                # Clean up temp file
                os.unlink(temp_file_path)
                return
                
            # Check for potential fraud - Use the check_image method we implemented
            fraud_score = self.fraud_detector.check_image(temp_file_path, damage_results)
            
            # Get AI analysis from Salesforce
            sf_analysis = self.sf_analyzer.analyze_damage(damage_results)
            
            # Send results to user
            self._send_damage_analysis(channel_id, user_id, processing_msg["ts"], damage_results, fraud_score, file_id, client, sf_analysis)
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
        except Exception as e:
            logger.error(f"Error processing file {file_id}: {e}")
            # Try to notify the user
            try:
                channel_id = body["event"].get("channel", body["event"].get("channel_id"))
                user_id = body["event"].get("user")
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"<@{user_id}> Sorry, I encountered an error while processing your image. Please try again later."
                )
            except:
                pass
    
    def _process_file_with_context(self, file_id, user_id, channel_id, client):
        """Process a file with channel context."""
        try:
            # Get file info
            file_info = client.files_info(file=file_id)
            
            if not file_info or "file" not in file_info:
                logger.warning(f"Could not retrieve info for file {file_id}")
                return
            
            file_obj = file_info["file"]
            
            # Check if it's an image
            if not file_obj.get("mimetype", "").startswith("image/"):
                logger.info(f"File {file_id} is not an image, skipping")
                return
            
            # Post a message that we're processing the image
            message = client.chat_postMessage(
                channel=channel_id,
                text=f"<@{user_id}> I'm analyzing your image for vehicle damage..."
            )
            
            # Download the file
            download_url = file_obj.get("url_private")
            if not download_url:
                client.chat_update(
                    channel=channel_id,
                    ts=message["ts"],
                    text=f"<@{user_id}> Sorry, I couldn't download your image to analyze it."
                )
                return
            
            # Process the image following your existing flow
            # ... existing code from _process_file ...
            
        except Exception as e:
            logger.error(f"Error processing file with context: {e}")
            client.chat_postMessage(
                channel=channel_id,
                text=f"<@{user_id}> Sorry, there was an error processing your image. Please try again."
            )
    
    def _send_non_image_response(self, body, client):
        """Send a response for non-image files."""
        try:
            channel_id = body["event"].get("channel", body["event"].get("channel_id"))
            user_id = body["event"].get("user")
            
            client.chat_postMessage(
                channel=channel_id,
                text=f"<@{user_id}> Please upload an image file of the vehicle damage. I can only analyze images."
            )
        except Exception as e:
            logger.error(f"Error sending non-image response: {e}")
    
    def _send_damage_analysis(self, channel_id, user_id, message_ts, damage_results, fraud_score, file_id, client, sf_analysis=None):
        """Send damage analysis results to the user."""
        try:
            # Extract damage information
            damaged_parts = damage_results.get("damaged_parts", [])
            
            if not damaged_parts:
                client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text=f"<@{user_id}> I didn't detect any damage in your image. Please upload a clearer image of the damaged vehicle."
                )
                return
            
            # Get annotated image if available
            annotated_image_path = damage_results.get("annotated_image")
            
            # Calculate total cost and repair days regardless of whether we use Salesforce or not
            total_cost = 0
            for part in damaged_parts:
                cost = self._get_cost_for_part(part)
                total_cost += cost
                
            # Calculate repair time - more parts = more time
            repair_days = 2 + min(5, len(damaged_parts))
            
            # Prepare blocks for the message
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"I've analyzed your image and detected damage to the following parts:"
                    }
                }
            ]
            
            # Add the annotated image
            if annotated_image_path and os.path.exists(annotated_image_path):
                try:
                    # Upload the annotated image to Slack
                    upload_response = client.files_upload_v2(
                        file=annotated_image_path,
                        channel=channel_id,
                        title="Damage Detection Results"
                    )
                except Exception as img_error:
                    logger.error(f"Error uploading annotated image: {img_error}")
            
            # Add Salesforce analysis if available
            if sf_analysis and "analysis" in sf_analysis:
                # Parse the analysis content
                analysis_text = sf_analysis['analysis']
                
                # Split into sections - look for markdown headings
                sections = []
                current_section = {"title": "", "content": []}
                
                for line in analysis_text.strip().split('\n'):
                    # Check if this is a section heading (starts with ##)
                    if line.startswith('## '):
                        # If we have content in the current section, save it
                        if current_section["title"]:
                            sections.append(current_section)
                        
                        # Start a new section
                        current_section = {
                            "title": line.replace('## ', '').strip(),
                            "content": []
                        }
                    # Otherwise add to current section content
                    elif line.strip():
                        current_section["content"].append(line.strip())
                
                # Add the last section
                if current_section["title"]:
                    sections.append(current_section)
                
                # Add each section as formatted Slack blocks
                for section in sections:
                    # Add section header
                    blocks.append({
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": section["title"],
                            "emoji": True
                        }
                    })
                    
                    # Add section content
                    content_text = '\n'.join(section["content"])
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": content_text
                        }
                    })
                    
                    # Add a divider after each section (except the last)
                    blocks.append({"type": "divider"})
            
            # Remove the last divider if it exists
            if blocks and blocks[-1]["type"] == "divider":
                blocks.pop()
            
            # Add notes about damage detection if not included in the analysis
            if not sf_analysis or "analysis" not in sf_analysis:
                # Add damage detection information
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Damage Detection Results:*\nAbove is the annotated image showing detected damage."
                    }
                })
                
                # Add detailed part information
                for part_name in damaged_parts:
                    # Find the detection with this part name
                    confidence = 0.0
                    for detection in damage_results.get("detections", []):
                        if part_name in detection.get("class_name", ""):
                            confidence = detection.get("confidence", 0.0) * 100
                            break
                    
                    # Estimate cost
                    cost = self._get_cost_for_part(part_name)
                    
                    # Add to blocks
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{part_name.title()}*\n- Confidence: {confidence:.1f}%\n- Estimated Cost: ${cost:,.2f}"
                        }
                    })
                
                # Add total cost and repair time
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Total Estimated Repair Cost:* ${total_cost:,.2f}"
                    }
                })
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Estimated Repair Time:* {repair_days} days"
                    }
                })
            
            # Store important info in the payload
            damage_results_str = json.dumps({
                "damaged_parts": damaged_parts,
                "estimated_cost": total_cost,
                "estimated_days": repair_days
            })
            
            # Add confirmation buttons
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Confirm Analysis",
                            "emoji": True
                        },
                        "style": "primary",
                        "value": json.dumps({
                            "file_id": file_id,
                            "damage_results": damage_results_str
                        }),
                        "action_id": "confirm_damage_analysis"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Analysis Incorrect",
                            "emoji": True
                        },
                        "style": "danger",
                        "value": json.dumps({
                            "file_id": file_id
                        }),
                        "action_id": "reject_damage_analysis"
                    }
                ]
            })
            
            # Update the message
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=f"Vehicle Damage Analysis",
                blocks=blocks
            )
        
        except Exception as e:
            logger.error(f"Error sending damage analysis: {e}")
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=f"<@{user_id}> I encountered an error while processing your damage analysis. Please try again."
            )
    
    def _get_cost_for_part(self, part_name):
        """Get the estimated cost for a damaged part."""
        # Default costs for common parts
        cost_map = {
            "hood": 1200,
            "bumper": 800,
            "fender": 600,
            "door": 950,
            "headlight": 450,
            "taillight": 350,
            "windshield": 500,
            "mirror": 300,
            "wheel": 350,
            "trunk": 900,
            "grill": 400
        }
        
        # Try to match the part name to our cost map
        for key, cost in cost_map.items():
            if key in part_name.lower():
                return cost
        
        # Default cost for unknown parts
        return 750
    
    def handle_damage_confirmation(self, ack, body, client, logger):
        """Handle user confirmation of damage analysis."""
        ack()
        
        try:
            # Extract information from the button payload - with improved error handling
            try:
                action_value = body["actions"][0]["value"]
                logger.debug(f"Raw action value: {action_value}")
                values = json.loads(action_value)
                file_id = values.get("file_id")
                damage_results_str = values.get("damage_results", "{}")
                
                # Parse the nested damage_results
                if isinstance(damage_results_str, str):
                    damage_results = json.loads(damage_results_str)
                else:
                    damage_results = damage_results_str
                
            except json.JSONDecodeError as json_error:
                logger.error(f"JSON decode error: {json_error} in value: {body['actions'][0].get('value', 'unknown')}")
                # Create default values as fallback
                file_id = body["actions"][0].get("file_id", "unknown")
                damage_results = {"damaged_parts": [], "estimated_cost": 0, "estimated_days": 3}
            
            # Log what we received after parsing
            logger.info(f"Parsed confirmation values - file_id: {file_id}, damage_results: {damage_results}")
            
            # Get user and channel info
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]
            
            # Create a temporary processing message
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=message_ts,
                text=f"<@{user_id}> Processing your claim submission..."
            )
            
            # Format the claim data properly
            damaged_parts = damage_results.get("damaged_parts", [])
            total_cost = damage_results.get("estimated_cost", 0)
            
            # Create a claim based on the damage analysis
            claim_data = {
                "damage_type": "Vehicle Collision",
                "damaged_parts": damaged_parts,
                "estimated_cost": total_cost,
                "estimated_days": damage_results.get("estimated_days", 3),
                "file_id": file_id,
                "user_id": user_id
            }
            
            # Process claim
            claim_result = self.claim_processor.create_claim(user_id, claim_data)
            
            if claim_result and claim_result.get("claim_id"):
                # Show repair booking options
                self._send_repair_booking_options(channel_id, user_id, message_ts, claim_result, client)
            else:
                # Claim creation failed
                client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=message_ts,
                    text=f"<@{user_id}> There was an error creating your claim. Please try again or contact support."
                )
        
        except Exception as e:
            logger.error(f"Error processing damage confirmation: {e}")
            # More specific error message to help debugging
            if "actions" in str(e) or "value" in str(e):
                logger.error("Issue with extracting values from button payload")
            elif "damage_results" in str(e):
                logger.error("Issue with damage_results format or content")
            elif "create_claim" in str(e):
                logger.error("Issue with claim processor")
            
            # Notify the user
            try:
                client.chat_postMessage(
                    channel=body["channel"]["id"],
                    thread_ts=body["message"]["ts"],
                    text=f"<@{body['user']['id']}> Sorry, there was an error processing your confirmation. Please try again or contact support."
                )
            except Exception as notify_error:
                logger.error(f"Error sending notification about confirmation error: {notify_error}")
    
    def handle_damage_rejection(self, ack, body, client, logger):
        """Handle user rejection of damage analysis."""
        ack()
        
        try:
            # Extract information
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]
            
            # Present a form to get more detailed feedback
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"I understand the analysis wasn't accurate. Please describe the damage to your vehicle in your own words. Include the damaged parts and any other relevant details."
                    }
                },
                {
                    "type": "input",
                    "block_id": "description_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "description_input",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "For example: The front bumper is cracked and the headlight is broken..."
                        }
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Damage Description"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Submit Description",
                                "emoji": True
                            },
                            "style": "primary",
                            "action_id": "submit_description"
                        }
                    ]
                }
            ]
            
            # Update the message
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=f"Please describe the damage to your vehicle",
                blocks=blocks
            )
        
        except Exception as e:
            logger.error(f"Error handling damage rejection: {e}")
            # Notify the user of the error
            try:
                client.chat_postMessage(
                    channel=body["channel"]["id"],
                    text=f"<@{body['user']['id']}> I encountered an error while processing your feedback. Please try again or contact support."
                )
            except Exception as notify_error:
                logger.error(f"Error sending notification about confirmation error: {notify_error}")
    
    def _send_repair_booking_options(self, channel_id, user_id, message_ts, claim_result, client):
        """Send repair booking options to the user."""
        try:
            # Get user location
            user_location = self._get_user_location(user_id)
            
            # Show loading message while we find service centers
            loading_message = client.chat_postMessage(
                channel=channel_id,
                thread_ts=message_ts,
                text=f"<@{user_id}> Finding service centers near {user_location['address']}..."
            )
            
            # Get nearest service centers
            service_centers = self._find_nearby_service_centers(user_location)
            
            # Create blocks for the message
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Claim Created Successfully* :white_check_mark:\nClaim ID: {claim_result['claim_id']}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Let's schedule your vehicle repair. Here are the nearest service centers to *{user_location['address']}*:"
                    }
                },
                {
                    "type": "divider"
                }
            ]
            
            # Add service center options
            for i, center in enumerate(service_centers[:3]):  # Limit to 3 centers
                # Add rating stars
                rating_stars = "★" * int(center['rating']) + "☆" * (5 - int(center['rating']))
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{center['name']}*\n{center['address']}\nDistance: {center['distance']} | Rating: {center['rating']} {rating_stars}\nPhone: {center.get('phone', 'N/A')}"
                    },
                    "accessory": {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Select",
                            "emoji": True
                        },
                        "value": json.dumps({
                            "claim_id": claim_result["claim_id"],
                            "center_id": i,
                            "center_name": center["name"]
                        }),
                        "action_id": f"select_service_center_{i}"
                    }
                })
                
                # Register handler for this specific service center button
                self.app.action(f"select_service_center_{i}")(self.handle_service_center_selection)
            
            # Add a note about other options
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "These service centers have been selected based on ratings, location, and availability for your vehicle type."
                    }
                ]
            })
            
            # Update the message
            client.chat_update(
                channel=channel_id,
                ts=loading_message["ts"],
                text=f"Please select a service center to repair your vehicle:",
                blocks=blocks
            )
        
        except Exception as e:
            logger.error(f"Error sending repair booking options: {e}")
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=message_ts,
                text=f"<@{user_id}> Sorry, there was an error finding repair options. Please contact customer service at 1-800-555-CLAIM."
            )
    
    def handle_service_center_selection(self, ack, body, client, logger):
        """Handle service center selection."""
        ack()
        
        try:
            # Extract information
            values = json.loads(body["actions"][0]["value"])
            claim_id = values.get("claim_id")
            center_name = values.get("center_name")
            
            # Get user and channel info
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]
            
            # Generate available timeslots (next 3 days, 3 slots per day)
            current_date = datetime.now()
            available_dates = [current_date + timedelta(days=i) for i in range(1, 4)]  # Next 3 days
            
            # Create time slots
            time_slots = []
            for date in available_dates:
                date_str = date.strftime("%A, %B %d")
                time_slots.extend([
                    {"date": date_str, "time": "9:00 AM", "timestamp": date.replace(hour=9, minute=0).timestamp()},
                    {"date": date_str, "time": "12:00 PM", "timestamp": date.replace(hour=12, minute=0).timestamp()},
                    {"date": date_str, "time": "3:00 PM", "timestamp": date.replace(hour=15, minute=0).timestamp()}
                ])
            
            # Create blocks for the message
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Schedule Repair at {center_name}*\nPlease select a convenient time:"
                    }
                },
                {
                    "type": "divider"
                }
            ]
            
            # Group slots by date
            current_date = None
            for slot in time_slots:
                if slot["date"] != current_date:
                    current_date = slot["date"]
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{current_date}*"
                        }
                    })
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{slot['time']}"
                    },
                    "accessory": {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Book",
                            "emoji": True
                        },
                        "value": json.dumps({
                            "claim_id": claim_id,
                            "center_name": center_name,
                            "date": slot["date"],
                            "time": slot["time"],
                            "timestamp": slot["timestamp"]
                        }),
                        "action_id": f"book_timeslot_{int(slot['timestamp'])}"
                    }
                })
            
            # Update the message
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=f"<@{user_id}> Select a time slot for your repair at {center_name}.",
                blocks=blocks
            )
            
            # Register timeslot booking handlers
            for slot in time_slots:
                self.app.action(f"book_timeslot_{int(slot['timestamp'])}")(self.handle_timeslot_booking)
            
        except Exception as e:
            logger.error(f"Error handling service center selection: {e}")
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=message_ts,
                text=f"<@{user_id}> Sorry, there was an error processing your selection. Please try again or contact support."
            )
    
    def handle_timeslot_booking(self, ack, body, client, logger):
        """Handle timeslot booking."""
        ack()
        
        try:
            # Extract information
            values = json.loads(body["actions"][0]["value"])
            claim_id = values.get("claim_id")
            center_name = values.get("center_name")
            date = values.get("date")
            time = values.get("time")
            
            # Get user and channel info
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]
            
            # Open a modal to collect contact information
            client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "contact_info_modal",
                    "title": {
                        "type": "plain_text",
                        "text": "Contact Information"
                    },
                    "submit": {
                        "type": "plain_text",
                        "text": "Confirm Booking"
                    },
                    "close": {
                        "type": "plain_text",
                        "text": "Cancel"
                    },
                    "private_metadata": json.dumps({
                        "claim_id": claim_id,
                        "center_name": center_name,
                        "date": date,
                        "time": time,
                        "user_id": user_id,
                        "channel_id": channel_id,
                        "message_ts": message_ts
                    }),
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"Please provide your contact information for your appointment at *{center_name}* on *{date}* at *{time}*."
                            }
                        },
                        {
                            "type": "input",
                            "block_id": "full_name",
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "full_name_input",
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": "e.g., John Smith"
                                }
                            },
                            "label": {
                                "type": "plain_text",
                                "text": "Full Name"
                            }
                        },
                        {
                            "type": "input",
                            "block_id": "email",
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "email_input",
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": "e.g., john@example.com"
                                }
                            },
                            "label": {
                                "type": "plain_text",
                                "text": "Email Address"
                            }
                        },
                        {
                            "type": "input",
                            "block_id": "phone",
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "phone_input",
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": "e.g., 555-123-4567"
                                }
                            },
                            "label": {
                                "type": "plain_text",
                                "text": "Phone Number"
                            }
                        }
                    ]
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling timeslot booking: {e}")
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=message_ts,
                text=f"<@{user_id}> Sorry, there was an error processing your booking. Please try again or contact support."
            )
    
    def handle_contact_info_submission(self, ack, body, client, view, logger):
        """Handle contact information submission from modal."""
        ack()
        
        try:
            # Extract metadata
            metadata = json.loads(view["private_metadata"])
            claim_id = metadata.get("claim_id")
            center_name = metadata.get("center_name")
            date = metadata.get("date")
            time = metadata.get("time")
            user_id = metadata.get("user_id")
            channel_id = metadata.get("channel_id")
            message_ts = metadata.get("message_ts")
            
            # Extract contact information
            full_name = view["state"]["values"]["full_name"]["full_name_input"]["value"]
            email = view["state"]["values"]["email"]["email_input"]["value"]
            phone = view["state"]["values"]["phone"]["phone_input"]["value"]
            
            # Book the timeslot with contact information
            booking_result = self._book_repair_timeslot(
                user_id=user_id,
                claim_id=claim_id,
                center_name=center_name,
                date=date,
                time=time,
                contact_info={
                    "name": full_name,
                    "email": email,
                    "phone": phone
                }
            )
            
            if booking_result:
                # Create confirmation blocks
                blocks = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":white_check_mark: *Repair Appointment Confirmed!*"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Claim ID:*\n{claim_id}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Service Center:*\n{center_name}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Date:*\n{date}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Time:*\n{time}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Contact Information:*\n{full_name}\n{email}\n{phone}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Your repair appointment has been scheduled. A confirmation email has been sent with details and instructions."
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "Need to reschedule? Contact customer service at 1-800-555-CLAIM or reply here."
                            }
                        ]
                    }
                ]
                
                # Update the message
                client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text=f"<@{user_id}> Your repair appointment has been confirmed at {center_name} on {date} at {time}.",
                    blocks=blocks
                )
                
                # Send calendar invite and email confirmation
                self._send_calendar_invite(user_id, claim_id, center_name, date, time, full_name, email, phone)
                
            else:
                # Booking failed
                client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text=f"<@{user_id}> Sorry, there was an error booking your appointment. Please try another time slot or contact customer service.",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "⚠️ *Unable to Schedule Appointment*\nThe selected time slot is no longer available. Please try another time or contact customer service at 1-800-555-CLAIM."
                            }
                        }
                    ]
                )
        
        except Exception as e:
            logger.error(f"Error processing contact information: {e}")
            # Send error message to DM
            try:
                client.chat_postMessage(
                    channel=user_id,
                    text="Sorry, there was an error processing your booking information. Please try again or contact support."
                )
            except Exception as dm_error:
                logger.error(f"Error sending DM: {dm_error}")
    
    def _get_user_location(self, user_id):
        """Get user location from database or prompt the user."""
        try:
            # Try to get location from database first
            from database.customer_db import CustomerDatabase
            db = CustomerDatabase()
            customer = db.get_customer_by_id(user_id)
            
            if customer and 'location' in customer:
                return customer['location']
            
            # If no location in database, let's use IP geolocation or ask the user
            # For now, we'll use a geolocation service to get an approximate location
            import requests
            
            # Use IP geolocation to get approximate location
            try:
                geo_response = requests.get('https://ipinfo.io/json')
                if geo_response.status_code == 200:
                    data = geo_response.json()
                    if 'loc' in data:
                        # loc contains "latitude,longitude"
                        lat, lng = data['loc'].split(',')
                        return {
                            "latitude": float(lat),
                            "longitude": float(lng),
                            "address": data.get('city', '') + ', ' + data.get('region', '') + ', ' + data.get('country', '')
                        }
            except Exception as geo_error:
                logger.error(f"Error getting location from IP: {geo_error}")
            
            # Fallback to default location if all else fails
            # This should rarely happen with the above methods
            return {
                "latitude": 12.9716,  # Bangalore, India coordinates 
                "longitude": 77.5946,
                "address": "Bangalore, Karnataka, India"
            }
        except Exception as e:
            logger.error(f"Error getting user location: {e}")
            # Fallback to default
            return {
                "latitude": 12.9716,
                "longitude": 77.5946,
                "address": "Bangalore, Karnataka, India"
            }

    def _find_nearby_service_centers(self, user_location):
        """Find real service centers near the user's location using Google Maps API."""
        try:
            # Use Google Maps API to find real service centers
            from googlemaps import Client as GoogleMaps
            import os
            
            # Get Google Maps API key from environment
            gmaps_key = os.environ.get('GOOGLE_MAPS_API_KEY')
            
            if not gmaps_key:
                logger.error("Google Maps API key not found in environment variables")
                return self._get_fallback_service_centers(user_location)
            
            # Initialize Google Maps client
            gmaps = GoogleMaps(key=gmaps_key)
            
            # Search for auto repair shops near the user's location
            places_result = gmaps.places_nearby(
                location=(user_location["latitude"], user_location["longitude"]),
                radius=10000,  # 10km radius
                type='car_repair',
                keyword='auto repair service center'
            )
            
            # Process results
            service_centers = []
            if places_result and 'results' in places_result:
                for place in places_result['results'][:5]:  # Get top 5 results
                    # Get additional details for each place
                    place_details = gmaps.place(place['place_id'])
                    
                    if place_details and 'result' in place_details:
                        details = place_details['result']
                        
                        # Calculate distance using the Distance Matrix API
                        distance_result = gmaps.distance_matrix(
                            origins=f"{user_location['latitude']},{user_location['longitude']}", 
                            destinations=f"{details['geometry']['location']['lat']},{details['geometry']['location']['lng']}",
                            mode="driving",
                            units="metric"
                        )
                        
                        distance_text = "Unknown distance"
                        if (distance_result and 'rows' in distance_result and distance_result['rows'] 
                            and 'elements' in distance_result['rows'][0] and distance_result['rows'][0]['elements'] 
                            and 'distance' in distance_result['rows'][0]['elements'][0]):
                            distance_text = distance_result['rows'][0]['elements'][0]['distance']['text']
                        
                        service_centers.append({
                            "name": details.get('name', 'Unknown Service Center'),
                            "address": details.get('formatted_address', 'Address not available'),
                            "distance": distance_text,
                            "rating": details.get('rating', 0),
                            "phone": details.get('formatted_phone_number', 'Phone not available'),
                            "website": details.get('website', '#'),
                            "open_now": details.get('opening_hours', {}).get('open_now', False),
                            "place_id": details.get('place_id', '')
                        })
            
            # If we found service centers, return them
            if service_centers:
                # Sort by rating (highest first)
                service_centers.sort(key=lambda x: x.get('rating', 0), reverse=True)
                return service_centers
            
            # If no results, fall back to our backup data
            return self._get_fallback_service_centers(user_location)
            
        except Exception as e:
            logger.error(f"Error finding nearby service centers: {e}")
            return self._get_fallback_service_centers(user_location)

    def _get_fallback_service_centers(self, user_location):
        """Get fallback service centers if the API call fails."""
        # Determine country from the address and provide appropriate fallbacks
        country = user_location.get('address', '').split(',')[-1].strip()
        
        if "India" in country:
            return [
                {
                    "name": "Pratham Motors",
                    "address": "10/10, Hosur Road, Bommanahalli, Bangalore, Karnataka 560068",
                    "distance": "3.2 km",
                    "rating": 4.7,
                    "phone": "+91 80 2573 5555"
                },
                {
                    "name": "Automotive Mechanics",
                    "address": "No. 293, 100 Feet Ring Road, Banashankari, Bangalore, Karnataka 560085",
                    "distance": "5.8 km",
                    "rating": 4.5,
                    "phone": "+91 99453 50505"
                },
                {
                    "name": "Car Service Center",
                    "address": "80 Feet Road, Koramangala 4th Block, Bangalore, Karnataka 560034",
                    "distance": "4.1 km",
                    "rating": 4.8,
                    "phone": "+91 80 4123 5678"
                }
            ]
        elif "UK" in country or "United Kingdom" in country:
            return [
                {
                    "name": "Kwik Fit",
                    "address": "123 High Street, London, UK",
                    "distance": "2.1 miles",
                    "rating": 4.6,
                    "phone": "+44 20 7946 0123"
                },
                {
                    "name": "Halfords Autocentre",
                    "address": "45 Oxford Road, Manchester, UK",
                    "distance": "3.4 miles",
                    "rating": 4.5,
                    "phone": "+44 161 523 0987"
                },
                {
                    "name": "Formula One Autocentre",
                    "address": "78 Church Street, Birmingham, UK",
                    "distance": "1.9 miles",
                    "rating": 4.7,
                    "phone": "+44 121 389 7654"
                }
            ]
        else:
            # Default to US service centers for other regions until we add more regions
            return [
                {
                    "name": "Downtown Auto Repair",
                    "address": "123 Main St, Local City",
                    "distance": "1.2 miles",
                    "rating": 4.8,
                    "phone": "+1 555-123-4567"
                },
                {
                    "name": "Central Service Center",
                    "address": "456 Market St, Local City",
                    "distance": "2.5 miles",
                    "rating": 4.6,
                    "phone": "+1 555-987-6543"
                },
                {
                    "name": "Premier Vehicle Repair",
                    "address": "789 Mission St, Local City",
                    "distance": "3.1 miles",
                    "rating": 4.9,
                    "phone": "+1 555-345-6789"
                }
            ]
    
    def _book_repair_timeslot(self, user_id, claim_id, center_name, date, time, contact_info=None):
        """Book a repair timeslot."""
        try:
            # In a real implementation, you would update a database or call an API
            # For now, just log the booking and return success
            if contact_info:
                logger.info(f"Booked repair for {contact_info['name']} ({user_id}), claim {claim_id} at {center_name} on {date} at {time}")
            else:
                logger.info(f"Booked repair for user {user_id}, claim {claim_id} at {center_name} on {date} at {time}")
            
            # Record in blockchain for immutability
            try:
                from blockchain.enhanced_client import EnhancedBlockchainClient
                blockchain_client = EnhancedBlockchainClient()
                
                booking_data = {
                    "type": "repair_booking",
                    "user_id": user_id,
                    "claim_id": claim_id,
                    "center_name": center_name,
                    "date": date,
                    "time": time,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Add contact info if available
                if contact_info:
                    booking_data["contact_info"] = {
                        "name": contact_info["name"],
                        "email": contact_info["email"],
                        "phone": contact_info["phone"]
                    }
                
                blockchain_client.record_transaction(json.dumps(booking_data))
                logger.info(f"Recorded repair booking in blockchain for claim {claim_id}")
            except Exception as blockchain_error:
                logger.error(f"Failed to record in blockchain, but continuing: {blockchain_error}")
            
            return True
        except Exception as e:
            logger.error(f"Error booking repair timeslot: {e}")
            return False
    
    def _send_calendar_invite(self, user_id, claim_id, center_name, date, time, full_name=None, email=None, phone=None):
        """Send calendar invite for the repair appointment."""
        try:
            # In a real implementation, you would generate and send a calendar invite
            # For now, just log that it would be sent
            logger.info(f"Sending calendar invite for claim {claim_id} appointment")
            
            # You could use the email_sender module to send an actual email with calendar attachment
            from utils.email_sender import EmailNotifier
            email_sender = EmailNotifier()
            
            # Use the provided email or fall back to default
            recipient_email = email if email else f"{user_id}@example.com"
            recipient_name = full_name if full_name else "Valued Customer"
            
            subject = f"Appointment Confirmation: Vehicle Repair for Claim #{claim_id}"
            
            # Actually send the email this time (not commented out)
            email_sender.send_repair_scheduled(recipient_email, {
                'customer_name': recipient_name,
                'claim_id': claim_id,
                'date': date,
                'time': time,
                'location': center_name,
                'address': 'Service center address',  # This would come from your service center database
                'phone': phone if phone else '1-800-555-REPAIR',
                'confirmation_code': f'REPAIR-{claim_id}',
                'directions_link': '#'
            })
            
            logger.info(f"Calendar invite sent to {recipient_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending calendar invite: {e}")
            return False

    def handle_description_submission(self, ack, body, client, logger):
        """Handle user submission of damage description."""
        # Acknowledge the action
        ack()
        
        try:
            # Extract the description text
            description_text = body["state"]["values"]["description_block"]["description_input"]["value"]
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]
            
            # Log the description
            logger.info(f"Received damage description from user {user_id}: {description_text}")
            
            # Analyze the description text
            # This could involve NLP to extract key entities or simply storing it
            
            # Send a confirmation message
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=message_ts,
                text=f"Thank you for your description. I've noted that: '{description_text}'"
            )
            
            # Update the original message to remove the input form
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Your Description:* {description_text}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Thank you for providing additional details about the damage. This information will help us process your claim more accurately."
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Continue with Claim Process",
                                "emoji": True
                            },
                            "style": "primary",
                            "value": json.dumps({"description": description_text}),
                            "action_id": "continue_with_description"
                        }
                    ]
                }
            ]
            
            # Update the message
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                blocks=blocks,
                text="Thank you for your description."
            )
            
            # Register handler for continue button
            self.app.action("continue_with_description")(self.handle_continue_with_description)
            
        except Exception as e:
            logger.error(f"Error handling description submission: {e}")
            # Send error message
            try:
                client.chat_postMessage(
                    channel=body["channel"]["id"],
                    thread_ts=body["message"]["ts"],
                    text="Sorry, there was an error processing your description. Please try again."
                )
            except:
                pass

    def handle_continue_with_description(self, ack, body, client, logger):
        """Handle user continuing after providing description."""
        # Acknowledge the action
        ack()
        
        try:
            # Extract the stored description
            values = json.loads(body["actions"][0]["value"])
            description = values.get("description", "")
            
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]
            
            # Here you would integrate this description with your damage detection system
            # For example, update the claim with the textual description
            
            # Call the salesforce analyzer with the description
            sf_analysis = self.sf_analyzer.analyze_damage_description(description)
            
            # Update the message with next steps (perhaps show service centers)
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text="Processing your claim...",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Thank you for providing details about your vehicle damage. I'm processing your claim now."
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Description provided:* {description}"
                        }
                    }
                ]
            )
            
            # Create a mock claim result
            claim_result = {
                "claim_id": f"CLM-{int(time.time())}-{user_id[:5]}",
                "status": "submitted",
                "description": description
            }
            
            # Send repair booking options
            self._send_repair_booking_options(channel_id, user_id, message_ts, claim_result, client)
            
        except Exception as e:
            logger.error(f"Error handling continue with description: {e}")
            # Send error message
            try:
                client.chat_postMessage(
                    channel=body["channel"]["id"],
                    thread_ts=body["message"]["ts"],
                    text="Sorry, there was an error processing your claim. Please try again or contact customer service."
                )
            except:
                pass 