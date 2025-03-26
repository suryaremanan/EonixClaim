"""
Slack handler for service scheduling with Salesforce Agentforce.
"""
import json
import logging
from slack_bolt import App
from slack_sdk import WebClient
from salesforce.agentforce_client import AgentforceClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Salesforce Agentforce client
agentforce_client = AgentforceClient()

def register_handlers(app: App):
    """Register scheduling handlers with the Slack app."""
    
    @app.action("schedule_repair")
    def handle_schedule_repair(ack, body, client, logger):
        """Handle the schedule repair button click."""
        # Always acknowledge the action request
        ack()
        
        try:
            # Extract claim ID and user info
            claim_id = body["actions"][0].get("value")
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            
            # Get available time slots
            slots_response = agentforce_client.get_available_time_slots()
            
            if not slots_response.get('success'):
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"Error retrieving available time slots: {slots_response.get('message')}"
                )
                return
            
            time_slots = slots_response.get('time_slots', [])
            
            # Group slots by date
            slots_by_date = {}
            for slot in time_slots:
                date = slot['date']
                if date not in slots_by_date:
                    slots_by_date[date] = []
                slots_by_date[date].append(slot)
            
            # Create a date selector
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Schedule Repair Service",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Please select a date for your repair service:"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "static_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Select a date",
                                "emoji": True
                            },
                            "options": [
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": f"{date} ({next(iter(slots)).get('day')})",
                                        "emoji": True
                                    },
                                    "value": date
                                } for date, slots in slots_by_date.items()
                            ],
                            "action_id": "select_date"
                        }
                    ]
                }
            ]
            
            # Store time slots in app state or a database
            # For this example, we'll store it in a global variable (not recommended for production)
            app.logger.info(f"Storing time slots for claim {claim_id}")
            
            # Open the modal
            client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text="Please select a date for your repair service"
            )
            
        except Exception as e:
            logger.error(f"Error handling schedule repair: {e}")
            client.chat_postMessage(
                channel=body["channel"]["id"],
                text=f"An error occurred while scheduling repair: {str(e)}"
            )
    
    @app.action("select_date")
    def handle_date_selection(ack, body, client, logger):
        """Handle date selection for scheduling."""
        # Always acknowledge the action request
        ack()
        
        try:
            # Extract selected date
            selected_date = body["actions"][0]["selected_option"]["value"]
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            
            # Get time slots for the selected date
            slots_response = agentforce_client.get_available_time_slots()
            time_slots = [slot for slot in slots_response.get('time_slots', []) if slot['date'] == selected_date]
            
            # Create time slot selectors
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Available Times for {selected_date}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Please select a time for your repair service:"
                    }
                }
            ]
            
            # Add buttons for each time slot
            for slot in time_slots:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{slot['start_time']} - {slot['end_time']}*"
                    },
                    "accessory": {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Select",
                            "emoji": True
                        },
                        "value": slot['id'],
                        "action_id": "select_time"
                    }
                })
            
            # Add a back button
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Back to Dates",
                            "emoji": True
                        },
                        "value": "back_to_dates",
                        "action_id": "back_to_dates"
                    }
                ]
            })
            
            # Update the message
            client.chat_update(
                channel=channel_id,
                ts=body["message"]["ts"],
                blocks=blocks,
                text=f"Available Times for {selected_date}"
            )
            
        except Exception as e:
            logger.error(f"Error handling date selection: {e}")
            client.chat_postMessage(
                channel=body["channel"]["id"],
                text=f"An error occurred while selecting a date: {str(e)}"
            )
    
    @app.action("select_time")
    def handle_time_selection(ack, body, client, logger):
        """Handle time slot selection for scheduling."""
        # Always acknowledge the action request
        ack()
        
        try:
            # Extract selected time slot
            selected_slot_id = body["actions"][0]["value"]
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            
            # Open a modal to collect customer information
            client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "customer_info_submission",
                    "title": {
                        "type": "plain_text",
                        "text": "Customer Information",
                        "emoji": True
                    },
                    "submit": {
                        "type": "plain_text",
                        "text": "Submit",
                        "emoji": True
                    },
                    "close": {
                        "type": "plain_text",
                        "text": "Cancel",
                        "emoji": True
                    },
                    "private_metadata": json.dumps({
                        "slot_id": selected_slot_id,
                        "channel_id": channel_id,
                        "message_ts": body["message"]["ts"]
                    }),
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "name_block",
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "name_input",
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": "Enter your full name"
                                }
                            },
                            "label": {
                                "type": "plain_text",
                                "text": "Name",
                                "emoji": True
                            }
                        },
                        {
                            "type": "input",
                            "block_id": "phone_block",
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "phone_input",
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": "Enter your phone number"
                                }
                            },
                            "label": {
                                "type": "plain_text",
                                "text": "Phone Number",
                                "emoji": True
                            }
                        },
                        {
                            "type": "input",
                            "block_id": "email_block",
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "email_input",
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": "Enter your email address"
                                }
                            },
                            "label": {
                                "type": "plain_text",
                                "text": "Email",
                                "emoji": True
                            }
                        }
                    ]
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling time selection: {e}")
            client.chat_postMessage(
                channel=body["channel"]["id"],
                text=f"An error occurred while selecting a time: {str(e)}"
            )
    
    @app.view("customer_info_submission")
    def handle_customer_info_submission(ack, body, client, view, logger):
        """Handle submission of customer information."""
        # Always acknowledge the view submission
        ack()
        
        try:
            # Extract submitted values
            values = view["state"]["values"]
            name = values["name_block"]["name_input"]["value"]
            phone = values["phone_block"]["phone_input"]["value"]
            email = values["email_block"]["email_input"]["value"]
            
            # Extract metadata
            metadata = json.loads(view["private_metadata"])
            slot_id = metadata["slot_id"]
            channel_id = metadata["channel_id"]
            message_ts = metadata["message_ts"]
            
            # Get claim ID (in production, this would be stored or passed through the flow)
            claim_id = "claim_12345"  # This would come from earlier in the flow
            
            # Schedule the service
            response = agentforce_client.schedule_service(
                claim_id=claim_id,
                time_slot_id=slot_id,
                customer_name=name,
                phone_number=phone,
                email=email
            )
            
            if response.get('success'):
                # Format appointment details
                details = response.get('details', {})
                
                # Update the message with confirmation
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🎉 Appointment Confirmed!",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Your vehicle repair has been scheduled!*"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Date:*\n{details.get('date')} ({details.get('day')})"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Time:*\n{details.get('time')}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Location:*\n{details.get('location')}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Confirmation Code:*\n{details.get('confirmation_code')}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "A confirmation email has been sent to your email address. Please arrive 15 minutes before your appointment time."
                        }
                    }
                ]
                
                # Update the original message
                client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    blocks=blocks,
                    text="Appointment Confirmed!"
                )
                
                # Send a confirmation DM to the user
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"Your repair appointment has been confirmed for {details.get('date')} at {details.get('time')}. Confirmation code: {details.get('confirmation_code')}"
                )
                
            else:
                # Notify the user of the error
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"There was an error scheduling your appointment: {response.get('message')}"
                )
                
        except Exception as e:
            logger.error(f"Error handling customer info submission: {e}")
            # Try to notify the user
            try:
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"An error occurred while scheduling your appointment: {str(e)}"
                )
            except:
                # If we can't DM the user, log the error
                logger.error("Could not notify user of error") 