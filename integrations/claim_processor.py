"""
Claim processor for the Eonix insurance platform.
Coordinates between all components to process claims end-to-end.
"""
import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
import time

from utils.email_sender import EmailNotifier
from utils.service_locator import ServiceLocator
from database.customer_db import CustomerDatabase
from blockchain.enhanced_client import EnhancedBlockchainClient
from slack_sdk import WebClient

# Configure logger
logger = logging.getLogger(__name__)

class ClaimProcessor:
    """
    Coordinates claim processing across all platform components.
    """
    
    def __init__(self):
        """Initialize the claim processor."""
        self.email = EmailNotifier()
        self.service_locator = ServiceLocator()
        self.db = CustomerDatabase()
        self.blockchain = EnhancedBlockchainClient()
        self.slack = WebClient(token=os.environ.get('SLACK_BOT_TOKEN'))
        
        logger.info("Claim processor initialized")
    
    def process_new_claim(self, customer_id: str, damage_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a new insurance claim end-to-end.
        
        Args:
            customer_id: Customer identifier
            damage_data: Damage assessment data
            
        Returns:
            Claim record if successful, None otherwise
        """
        try:
            # Get customer data
            customer = self.db.get_customer(customer_id)
            if not customer:
                logger.error(f"Customer not found: {customer_id}")
                return None
            
            # Generate claim ID
            timestamp = datetime.now()
            claim_id = f"CL-{timestamp.strftime('%Y%m%d%H%M')}-{customer_id[-4:]}"
            
            # Record on blockchain
            blockchain_id = self.blockchain.generate_unique_claim_id(customer_id)
            
            blockchain_data = {
                'customer_id': customer_id,
                'claim_date': timestamp.isoformat(),
                'damage_type': damage_data.get('damage_type', 'Vehicle damage'),
                'severity': damage_data.get('severity', 'Unknown'),
                'estimated_amount': damage_data.get('estimated_cost', 0)
            }
            
            tx_hash = self.blockchain.record_claim(
                blockchain_id,
                customer_id,
                customer.get('policy_number', 'UNKNOWN'),
                blockchain_data
            )
            
            # Create claim record for database
            claim_data = {
                'id': claim_id,
                'customer_id': customer_id,
                'policy_number': customer.get('policy_number'),
                'claim_date': timestamp.isoformat(),
                'damage_type': damage_data.get('damage_type', 'Vehicle damage'),
                'severity': damage_data.get('severity', 'Unknown'),
                'status': 'Submitted',
                'amount': damage_data.get('estimated_cost', 0),
                'repair_time': damage_data.get('repair_time', 'Unknown'),
                'blockchain_id': blockchain_id,
                'blockchain_tx': tx_hash,
                'metadata': json.dumps({
                    'damage_parts': damage_data.get('damaged_parts', []),
                    'damage_description': damage_data.get('damage_description', ''),
                    'image_path': damage_data.get('image_path', '')
                })
            }
            
            # Store in database
            claim_id = self.db.add_claim(claim_data)
            
            if not claim_id:
                logger.error("Failed to store claim in database")
                return None
            
            # Prepare data for email
            email_data = {
                'customer_name': customer.get('name', 'Valued Customer'),
                'claim_id': claim_id,
                'damage_description': damage_data.get('damage_description', 'Vehicle damage'),
                'estimated_cost': damage_data.get('estimated_cost', 0),
                'repair_time': damage_data.get('repair_time', 'Unknown'),
                'blockchain_id': blockchain_id,
                'adjuster_name': 'Alex Johnson',
                'adjuster_phone': '(555) 123-4567',
                'image_path': damage_data.get('image_path')
            }
            
            # Send email notification
            if 'email' in customer and customer['email']:
                self.email.send_claim_confirmation(customer['email'], email_data)
            
            logger.info(f"Claim processed successfully: {claim_id}")
            return claim_data
            
        except Exception as e:
            logger.error(f"Error processing claim: {e}")
            return None
    
    def schedule_repair(self, claim_id: str, location: str, 
                      date: str, time: str) -> Optional[Dict[str, Any]]:
        """
        Schedule a repair appointment for a claim.
        
        Args:
            claim_id: Claim identifier
            location: Customer location for finding nearby service stations
            date: Appointment date (YYYY-MM-DD)
            time: Appointment time (HH:MM)
            
        Returns:
            Appointment data if successful, None otherwise
        """
        try:
            # Get claim data
            claim = self.db.get_claim(claim_id)
            if not claim:
                logger.error(f"Claim not found: {claim_id}")
                return None
            
            # Get customer data
            customer = self.db.get_customer(claim['customer_id'])
            if not customer:
                logger.error(f"Customer not found: {claim['customer_id']}")
                return None
            
            # Find nearby service stations
            nearby_stations = self.service_locator.find_nearby_stations(location)
            
            if not nearby_stations:
                logger.error(f"No service stations found near: {location}")
                return None
            
            # Use the closest service station
            station = nearby_stations[0]
            
            # Generate confirmation code
            import random
            import string
            confirmation_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            # Create appointment record
            appointment_data = {
                'claim_id': claim_id,
                'customer_id': customer['id'],
                'appointment_date': f"{date} {time}",
                'location': station['name'],
                'address': station['address'],
                'status': 'Scheduled',
                'confirmation_code': confirmation_code,
                'service_station_id': station['id'],
                'metadata': json.dumps({
                    'station_phone': station['phone'],
                    'station_email': station.get('email', ''),
                    'directions_link': station.get('directions_link', ''),
                    'distance_miles': station.get('distance_miles', '')
                })
            }
            
            # Store in database
            appointment_id = self.db.add_appointment(appointment_data)
            
            if not appointment_id:
                logger.error("Failed to store appointment in database")
                return None
            
            # Prepare data for email
            email_data = {
                'customer_name': customer.get('name', 'Valued Customer'),
                'claim_id': claim_id,
                'date': date,
                'time': time,
                'location': station['name'],
                'address': station['address'],
                'phone': station['phone'],
                'confirmation_code': confirmation_code,
                'directions_link': station.get('directions_link', '#')
            }
            
            # Send email notification
            if 'email' in customer and customer['email']:
                self.email.send_repair_scheduled(customer['email'], email_data)
            
            logger.info(f"Repair appointment scheduled: {appointment_id}")
            
            # Add appointment ID to return data
            appointment_data['id'] = appointment_id
            
            return appointment_data
            
        except Exception as e:
            logger.error(f"Error scheduling repair: {e}")
            return None

    def create_claim(self, user_id, claim_data):
        """
        Create a new insurance claim.
        
        Args:
            user_id: The ID of the user submitting the claim
            claim_data: Dictionary containing claim details
                - damage_type: Type of damage (e.g., "Vehicle Collision")
                - damaged_parts: List of damaged vehicle parts
                - estimated_cost: Estimated repair cost
                - estimated_days: Estimated repair time in days
                - file_id: ID of the uploaded damage image
                
        Returns:
            Dictionary with claim details including claim_id on success,
            None on failure
        """
        try:
            # Generate a unique claim ID (in real system, would come from a database)
            timestamp = int(time.time())
            claim_id = f"CLM-{timestamp}-{user_id[:5]}"
            
            # Store claim data in our system
            claim_record = {
                "claim_id": claim_id,
                "user_id": user_id,
                "status": "submitted",
                "submission_date": datetime.now().isoformat(),
                "damage_type": claim_data.get("damage_type", "Unspecified"),
                "damaged_parts": claim_data.get("damaged_parts", []),
                "estimated_cost": claim_data.get("estimated_cost", 0),
                "estimated_days": claim_data.get("estimated_days", 0),
                "file_id": claim_data.get("file_id", "")
            }
            
            # Log claim creation
            logger.info(f"Creating new claim {claim_id} for user {user_id}")
            
            # In a real system, we would store this in a database
            # For now, just log it
            
            # Record in blockchain for immutability
            try:
                from blockchain.enhanced_client import EnhancedBlockchainClient
                blockchain_client = EnhancedBlockchainClient()
                
                # Record claim in blockchain
                blockchain_client.record_transaction(json.dumps({
                    "type": "claim_creation",
                    "claim_id": claim_id,
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    "estimated_cost": claim_data.get("estimated_cost", 0),
                    "damaged_parts": claim_data.get("damaged_parts", [])
                }))
                
                logger.info(f"Recorded claim {claim_id} in blockchain")
            except Exception as blockchain_error:
                logger.error(f"Failed to record claim in blockchain, but continuing: {blockchain_error}")
            
            # Return the claim record
            return claim_record
            
        except Exception as e:
            logger.error(f"Error creating claim: {e}")
            return None 