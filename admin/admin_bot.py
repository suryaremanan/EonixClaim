"""
Admin chat bot for the Eonix insurance platform.
Provides administrative capabilities through Slack.
"""
import os
import logging
import json
import tempfile
from typing import Dict, List, Any, Optional
from datetime import datetime
from slack_bolt import App

from database.customer_db import CustomerDatabase
from blockchain.enhanced_client import EnhancedBlockchainClient
from utils.service_locator import ServiceLocator

# Configure logger
logger = logging.getLogger(__name__)

class AdminBot:
    """
    Administrative chat bot for the Eonix platform.
    Handles admin queries and management functions through Slack.
    """
    
    def __init__(self, app: App):
        """
        Initialize the admin bot.
        
        Args:
            app: Slack Bolt App instance
        """
        self.app = app
        self.db = CustomerDatabase()
        self.blockchain = EnhancedBlockchainClient()
        self.service_locator = ServiceLocator()
        
        # Admin user IDs (from environment variable or hardcoded list)
        admin_ids_str = os.environ.get('ADMIN_USER_IDS', '')
        self.admin_user_ids = [id.strip() for id in admin_ids_str.split(',') if id.strip()]
        
        # Register command handlers
        self.register_handlers()
        
        logger.info("Admin bot initialized")
    
    def register_handlers(self):
        """Register all Slack command and message handlers."""
        # Admin commands
        self.app.command("/admin-query", self._handle_admin_query)
        self.app.command("/export-data", self._handle_export_data)
        self.app.command("/verify-blockchain", self._handle_verify_blockchain)
        
        # Admin message handler (for natural language queries)
        self.app.message("admin: ")(self._handle_admin_message)
    
    def _is_admin(self, user_id: str) -> bool:
        """
        Check if a user is an admin.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            True if user is an admin, False otherwise
        """
        return user_id in self.admin_user_ids
    
    def _handle_admin_query(self, ack, command, client):
        """
        Handle the /admin-query Slack command.
        
        Args:
            ack: Function to acknowledge the command
            command: Command data
            client: Slack client
        """
        # Acknowledge the command
        ack()
        
        # Check if user is admin
        if not self._is_admin(command['user_id']):
            client.chat_postEphemeral(
                channel=command['channel_id'],
                user=command['user_id'],
                text="⚠️ You don't have permission to use admin commands."
            )
            return
        
        # Parse query
        query_text = command['text'].strip()
        
        if not query_text:
            client.chat_postEphemeral(
                channel=command['channel_id'],
                user=command['user_id'],
                text="Please specify a query. Format: `customer <id>`, `claim <id>`, or `policy <number>`"
            )
            return
        
        # Process query
        parts = query_text.split(' ')
        query_type = parts[0].lower()
        query_value = ' '.join(parts[1:])
        
        if query_type == 'customer':
            self._query_customer(client, command['channel_id'], query_value)
        elif query_type == 'claim':
            self._query_claim(client, command['channel_id'], query_value)
        elif query_type == 'policy':
            self._query_policy(client, command['channel_id'], query_value)
        else:
            client.chat_postEphemeral(
                channel=command['channel_id'],
                user=command['user_id'],
                text=f"Unknown query type: {query_type}. Available types: customer, claim, policy"
            )
    
    def _query_customer(self, client, channel_id, customer_id):
        """Query customer information."""
        try:
            customer = self.db.get_customer(customer_id)
            
            if not customer:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"No customer found with ID: {customer_id}"
                )
                return
            
            # Get customer claims
            claims = self.db.get_customer_claims(customer_id)
            
            # Get customer appointments
            appointments = self.db.get_customer_appointments(customer_id)
            
            # Format the response
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Customer: {customer['name']}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*ID:* {customer['id']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Email:* {customer['email']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Phone:* {customer.get('phone', 'N/A')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Policy:* {customer.get('policy_number', 'N/A')}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Address:*\n{customer.get('address', 'N/A')}"
                    }
                },
                {
                    "type": "divider"
                }
            ]
            
            # Add claims
            if claims:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Claims ({len(claims)}):*"
                    }
                })
                
                for claim in claims:
                    blocks.append({
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Claim ID:* {claim['id']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Date:* {claim['claim_date']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Status:* {claim['status']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Amount:* ${float(claim.get('amount', 0)):.2f}"
                            }
                        ]
                    })
            else:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Claims:* No claims found"
                    }
                })
            
            # Add appointments
            if appointments:
                blocks.append({
                    "type": "divider"
                })
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Appointments ({len(appointments)}):*"
                    }
                })
                
                for appointment in appointments:
                    blocks.append({
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Date:* {appointment['appointment_date']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Status:* {appointment['status']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Location:* {appointment.get('location', 'N/A')}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Confirmation:* {appointment.get('confirmation_code', 'N/A')}"
                            }
                        ]
                    })
            
            # Send the message
            client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text=f"Customer information for {customer['name']}"
            )
            
        except Exception as e:
            logger.error(f"Error querying customer {customer_id}: {e}")
            client.chat_postMessage(
                channel=channel_id,
                text=f"Error retrieving customer information: {str(e)}"
            )
    
    def _handle_export_data(self, ack, command, client):
        """Handle the /export-data Slack command."""
        # Acknowledge the command
        ack()
        
        # Check if user is admin
        if not self._is_admin(command['user_id']):
            client.chat_postEphemeral(
                channel=command['channel_id'],
                user=command['user_id'],
                text="⚠️ You don't have permission to use admin commands."
            )
            return
        
        try:
            # Send initial response
            client.chat_postMessage(
                channel=command['channel_id'],
                text="Exporting data... This may take a moment."
            )
            
            # Export data to CSV
            export_dir = self.db.export_to_csv()
            
            if not export_dir:
                client.chat_postMessage(
                    channel=command['channel_id'],
                    text="Failed to export data. Check server logs for details."
                )
                return
            
            # Create a zip file of the export
            import shutil
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_path = os.path.join(tempfile.gettempdir(), f'eonix_export_{timestamp}.zip')
            
            shutil.make_archive(
                os.path.splitext(zip_path)[0],  # Remove .zip extension
                'zip',
                export_dir
            )
            
            # Upload the zip file
            client.files_upload_v2(
                file=zip_path,
                channel_id=command['channel_id'],
                title=f"Eonix Data Export {timestamp}",
                initial_comment="Here's the exported data from the Eonix platform."
            )
            
            # Clean up
            os.remove(zip_path)
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            client.chat_postMessage(
                channel=command['channel_id'],
                text=f"Error exporting data: {str(e)}"
            )
    
    def _handle_verify_blockchain(self, ack, command, client):
        """Handle the /verify-blockchain Slack command."""
        # Acknowledge the command
        ack()
        
        # Check if user is admin
        if not self._is_admin(command['user_id']):
            client.chat_postEphemeral(
                channel=command['channel_id'],
                user=command['user_id'],
                text="⚠️ You don't have permission to use admin commands."
            )
            return
        
        # Parse blockchain ID
        blockchain_id = command['text'].strip()
        
        if not blockchain_id:
            client.chat_postEphemeral(
                channel=command['channel_id'],
                user=command['user_id'],
                text="Please provide a blockchain ID to verify."
            )
            return
        
        try:
            # Send initial response
            client.chat_postMessage(
                channel=command['channel_id'],
                text=f"Verifying blockchain record: {blockchain_id}..."
            )
            
            # Verify on blockchain
            verification = self.blockchain.verify_claim(blockchain_id)
            
            if verification.get('verified'):
                # Format timestamp
                timestamp = datetime.fromtimestamp(verification['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                
                # Create message blocks
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Blockchain Verification Successful"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Blockchain ID:* {blockchain_id}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Policy Number:* {verification['policy_number']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Recorded:* {timestamp}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Claim Data:*"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"```{json.dumps(verification['claim_data'], indent=2)}```"
                        }
                    }
                ]
                
                client.chat_postMessage(
                    channel=command['channel_id'],
                    blocks=blocks,
                    text=f"Blockchain verification successful for ID: {blockchain_id}"
                )
            else:
                client.chat_postMessage(
                    channel=command['channel_id'],
                    text=f"❌ Blockchain verification failed: {verification.get('error', 'Unknown error')}"
                )
                
        except Exception as e:
            logger.error(f"Error verifying blockchain record: {e}")
            client.chat_postMessage(
                channel=command['channel_id'],
                text=f"Error verifying blockchain record: {str(e)}"
            )
    
    def _handle_admin_message(self, message, client):
        """Handle admin: prefixed messages."""
        # Extract the actual query (remove "admin: " prefix)
        query = message['text'][7:].strip()
        
        # Check if user is admin
        if not self._is_admin(message['user']):
            client.chat_postEphemeral(
                channel=message['channel'],
                user=message['user'],
                text="⚠️ You don't have permission to use admin commands."
            )
            return
        
        # Parse natural language query
        if query.lower().startswith('find customer'):
            # Extract customer info
            customer_info = query[13:].strip()
            self._natural_language_customer_search(client, message['channel'], customer_info)
        elif query.lower().startswith('export data'):
            # Handle like /export-data command
            client.chat_postMessage(
                channel=message['channel'],
                text="Starting data export..."
            )
            try:
                export_dir = self.db.export_to_csv()
                if export_dir:
                    client.chat_postMessage(
                        channel=message['channel'],
                        text=f"Data exported successfully to {export_dir}"
                    )
                else:
                    client.chat_postMessage(
                        channel=message['channel'],
                        text="Failed to export data. Check server logs for details."
                    )
            except Exception as e:
                client.chat_postMessage(
                    channel=message['channel'],
                    text=f"Error exporting data: {str(e)}"
                )
        else:
            # Default response for unknown queries
            client.chat_postMessage(
                channel=message['channel'],
                text="I didn't understand that admin command. Try:\n- `admin: find customer <name/email/id>`\n- `admin: export data`"
            )
    
    def _natural_language_customer_search(self, client, channel, customer_info):
        """Search for a customer based on natural language input."""
        try:
            # Try different search methods
            customers = []
            
            # Try by ID first
            customer = self.db.get_customer(customer_info)
            if customer:
                customers = [customer]
            
            # Try by email
            if not customers and '@' in customer_info:
                customers = self.db.search_customers({'email': customer_info})
            
            # Try by name
            if not customers:
                customers = self.db.search_customers({'name': customer_info})
            
            # Try by policy number
            if not customers:
                customers = self.db.search_customers({'policy_number': customer_info})
            
            if not customers:
                client.chat_postMessage(
                    channel=channel,
                    text=f"No customers found matching '{customer_info}'"
                )
                return
            
            if len(customers) == 1:
                # Just one customer found, show details
                self._query_customer(client, channel, customers[0]['id'])
            else:
                # Multiple customers found, show list
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"Found {len(customers)} matching customers:"
                        }
                    }
                ]
                
                for customer in customers:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{customer['name']}*\nID: {customer['id']} | Email: {customer['email']}"
                        },
                        "accessory": {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Details"
                            },
                            "value": customer['id'],
                            "action_id": "view_customer_details"
                        }
                    })
                
                client.chat_postMessage(
                    channel=channel,
                    blocks=blocks,
                    text=f"Found {len(customers)} matching customers"
                )
                
        except Exception as e:
            logger.error(f"Error in natural language customer search: {e}")
            client.chat_postMessage(
                channel=channel,
                text=f"Error searching for customers: {str(e)}"
            ) 