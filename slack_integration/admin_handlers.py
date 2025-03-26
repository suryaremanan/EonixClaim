"""
Admin functionality for the Eonix insurance platform Slack app.
Provides administrative commands and dashboards.
"""
import logging
import json
from datetime import datetime, timedelta
from slack_bolt import App
from database.appointment_db import AppointmentDatabase
from database.customer_db import CustomerDatabase
from utils.slack_auth import is_admin_user

# Configure logger
logger = logging.getLogger(__name__)

class AdminHandler:
    """
    Handles admin commands and dashboards for the Slack interface.
    """
    
    def __init__(self, app: App):
        """
        Initialize the admin handler.
        
        Args:
            app: Slack Bolt App instance
        """
        self.app = app
        self.appointment_db = AppointmentDatabase()
        self.customer_db = CustomerDatabase()
        
        # Register handlers
        self._register_handlers()
        
        logger.info("Admin handler initialized")
    
    def _register_handlers(self):
        """Register command handlers with the Slack app."""
        # Register the /admin-appointments command
        self.app.command("/admin-appointments")(self.handle_admin_appointments)
        
        # Register action handlers for appointment management
        self.app.action("admin_view_appointment_details")(self.handle_view_appointment_details)
        self.app.action("admin_reschedule_appointment")(self.handle_reschedule_appointment)
        self.app.action("admin_cancel_appointment")(self.handle_cancel_appointment)
        
        # Filter dropdown for admin dashboard
        self.app.action("admin_filter_appointments")(self.handle_filter_appointments)
    
    def handle_admin_appointments(self, ack, command, client, logger):
        """
        Handle /admin-appointments command.
        
        Args:
            ack: Acknowledge function
            command: Command payload
            client: Slack WebClient
            logger: Logger instance
        """
        # Add this line for debugging
        logger.info(f"Received admin-appointments command from user {command['user_id']}")
        
        # Acknowledge the command
        ack()
        
        try:
            # Check if the user is an admin
            user_id = command["user_id"]
            if not is_admin_user(user_id):
                client.chat_postEphemeral(
                    channel=command["channel_id"],
                    user=user_id,
                    text="Sorry, you don't have permission to access the admin dashboard."
                )
                return
            
            # Get appointment data - by default show upcoming appointments for the next 7 days
            filter_days = 7
            appointments = self.appointment_db.get_appointments(days=filter_days)
            
            # Create blocks for the admin dashboard
            blocks = self._create_appointment_dashboard_blocks(appointments, filter_days)
            
            # Send the dashboard as an ephemeral message (only visible to the admin)
            client.chat_postEphemeral(
                channel=command["channel_id"],
                user=user_id,
                text=f"Admin Dashboard - Appointments for next {filter_days} days",
                blocks=blocks
            )
            
        except Exception as e:
            logger.error(f"Error handling admin appointments command: {e}")
            client.chat_postEphemeral(
                channel=command["channel_id"],
                user=command["user_id"],
                text="Sorry, there was an error loading the admin dashboard."
            )
    
    def _create_appointment_dashboard_blocks(self, appointments, filter_days):
        """
        Create blocks for the appointment dashboard.
        
        Args:
            appointments: List of appointment objects
            filter_days: Number of days to filter for
            
        Returns:
            List of blocks for the dashboard
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📅 Eonix Admin Dashboard - Appointments",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Showing appointments for the next *{filter_days} days*. Use the filter to change the view."
                },
                "accessory": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Filter appointments",
                        "emoji": True
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Today",
                                "emoji": True
                            },
                            "value": "1"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Next 3 days",
                                "emoji": True
                            },
                            "value": "3"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Next 7 days",
                                "emoji": True
                            },
                            "value": "7"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Next 14 days",
                                "emoji": True
                            },
                            "value": "14"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Next 30 days",
                                "emoji": True
                            },
                            "value": "30"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "All appointments",
                                "emoji": True
                            },
                            "value": "all"
                        }
                    ],
                    "action_id": "admin_filter_appointments"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # Add summary stats
        today_count = sum(1 for a in appointments if a.get('date') == datetime.now().strftime('%Y-%m-%d'))
        
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Total Appointments:*\n{len(appointments)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Today's Appointments:*\n{today_count}"
                }
            ]
        })
        
        blocks.append({
            "type": "divider"
        })
        
        # If no appointments, show a message
        if not appointments:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No appointments found for the selected time period."
                }
            })
            return blocks
        
        # Group appointments by date
        appointments_by_date = {}
        for appointment in appointments:
            date = appointment.get('date', 'Unknown')
            if date not in appointments_by_date:
                appointments_by_date[date] = []
            appointments_by_date[date].append(appointment)
        
        # Add appointments grouped by date
        for date, date_appointments in sorted(appointments_by_date.items()):
            # Format date
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%A, %B %d, %Y')
            except:
                formatted_date = date
            
            blocks.append({
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": formatted_date,
                    "emoji": True
                }
            })
            
            # Add each appointment for this date
            for appointment in date_appointments:
                customer_name = appointment.get('customer_name', 'Unknown')
                time = appointment.get('time', 'Unknown')
                claim_id = appointment.get('claim_id', 'Unknown')
                service_center = appointment.get('service_center', 'Unknown location')
                status = appointment.get('status', 'scheduled')
                
                # Format the status with an appropriate emoji
                status_emoji = "✅" if status == "scheduled" else "⚠️" if status == "pending" else "❌" if status == "cancelled" else "🔄"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{time}* - {customer_name}\nClaim: {claim_id}\nLocation: {service_center}\nStatus: {status_emoji} {status.title()}"
                    },
                    "accessory": {
                        "type": "overflow",
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "View Details",
                                    "emoji": True
                                },
                                "value": json.dumps({"action": "view", "id": appointment.get('id')})
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Reschedule",
                                    "emoji": True
                                },
                                "value": json.dumps({"action": "reschedule", "id": appointment.get('id')})
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Cancel Appointment",
                                    "emoji": True
                                },
                                "value": json.dumps({"action": "cancel", "id": appointment.get('id')})
                            }
                        ],
                        "action_id": "admin_appointment_actions"
                    }
                })
            
            blocks.append({
                "type": "divider"
            })
        
        # Add export button
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Export to CSV",
                        "emoji": True
                    },
                    "value": json.dumps({"days": filter_days}),
                    "action_id": "admin_export_appointments"
                }
            ]
        })
        
        return blocks
    
    def handle_view_appointment_details(self, ack, body, client, logger):
        """Handle viewing appointment details."""
        ack()
        
        try:
            # Extract appointment ID
            values = json.loads(body["actions"][0]["value"])
            appointment_id = values.get("id")
            
            # Get the appointment
            appointment = self.appointment_db.get_appointment_by_id(appointment_id)
            
            if not appointment:
                client.chat_postEphemeral(
                    channel=body["channel"]["id"],
                    user=body["user"]["id"],
                    text="Sorry, the appointment couldn't be found."
                )
                return
            
            # Get customer details
            customer = self.customer_db.get_customer_by_id(appointment.get("customer_id", ""))
            
            # Create modal with appointment details
            client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "title": {
                        "type": "plain_text",
                        "text": f"Appointment Details"
                    },
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Claim ID:* {appointment.get('claim_id', 'Unknown')}"
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Customer:*\n{appointment.get('customer_name', 'Unknown')}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Date & Time:*\n{appointment.get('date', 'Unknown')} at {appointment.get('time', 'Unknown')}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Service Center:*\n{appointment.get('service_center', 'Unknown')}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Status:*\n{appointment.get('status', 'scheduled').title()}"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*Contact Information:*"
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Phone:*\n{customer.get('phone', 'Unknown')}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Email:*\n{customer.get('email', 'Unknown')}"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*Vehicle Details:*"
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Make:*\n{customer.get('vehicle', {}).get('make', 'Unknown')}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Model:*\n{customer.get('vehicle', {}).get('model', 'Unknown')}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Year:*\n{customer.get('vehicle', {}).get('year', 'Unknown')}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Color:*\n{customer.get('vehicle', {}).get('color', 'Unknown')}"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Notes:*\n{appointment.get('notes', 'No notes available')}"
                            }
                        }
                    ],
                    "close": {
                        "type": "plain_text",
                        "text": "Close"
                    }
                }
            )
        
        except Exception as e:
            logger.error(f"Error viewing appointment details: {e}")
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=body["user"]["id"],
                text="Sorry, there was an error viewing the appointment details."
            )
    
    def handle_filter_appointments(self, ack, body, client, logger):
        """Handle filtering appointments by date range."""
        ack()
        
        try:
            # Extract the filter value
            filter_value = body["actions"][0]["selected_option"]["value"]
            
            if filter_value == "all":
                filter_days = None
            else:
                filter_days = int(filter_value)
            
            # Get appointments
            appointments = self.appointment_db.get_appointments(days=filter_days)
            
            # Create updated blocks
            blocks = self._create_appointment_dashboard_blocks(appointments, filter_days or "all")
            
            # Update the message
            client.chat_update(
                channel=body["channel"]["id"],
                ts=body["message"]["ts"],
                text=f"Admin Dashboard - Appointments",
                blocks=blocks
            )
        
        except Exception as e:
            logger.error(f"Error filtering appointments: {e}")
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=body["user"]["id"],
                text="Sorry, there was an error filtering the appointments."
            ) 