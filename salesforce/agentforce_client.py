"""
Salesforce Agentforce 2.0 integration module.
Handles interactions with Salesforce AI agents for scheduling and service automation.
"""
import os
import logging
import json
from datetime import datetime, timedelta
from simple_salesforce import Salesforce
from config.config import SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN, SF_DOMAIN

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentforceClient:
    """
    Client for interacting with Salesforce Agentforce 2.0.
    Handles authentication, API calls, and response processing.
    """
    
    def __init__(self):
        """Initialize the Agentforce client with Salesforce credentials."""
        self.sf = None
        self.connect()
        
    def connect(self):
        """Connect to Salesforce API."""
        try:
            # For demo mode, if credentials are missing, just log a warning
            if not all([SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN]):
                logger.warning("Salesforce credentials not fully configured. Running in demo mode.")
                return
            
            # Fix domain duplication issue
            domain = SF_DOMAIN
            # If domain contains '.salesforce.com', remove it to prevent duplication
            if domain and '.salesforce.com' in domain:
                domain = domain.replace('.salesforce.com', '')
            
            self.sf = Salesforce(
                username=SF_USERNAME,
                password=SF_PASSWORD,
                security_token=SF_SECURITY_TOKEN,
                domain=domain  # Use the corrected domain
            )
            logger.info("Connected to Salesforce")
        except Exception as e:
            logger.error(f"Failed to connect to Salesforce: {e}")
            logger.warning("Running in demo mode without Salesforce connection")
    
    def create_claim(self, damage_assessment):
        """
        Create a new claim in Salesforce based on damage assessment.
        
        Args:
            damage_assessment: Dictionary containing damage assessment details
            
        Returns:
            Dictionary with claim ID and status
        """
        try:
            # Format data for Salesforce
            claim_data = {
                'Damage_Severity__c': damage_assessment.get('severity', 'Unknown'),
                'Estimated_Cost__c': damage_assessment.get('estimated_repair_cost', 0),
                'Damaged_Parts__c': ', '.join(damage_assessment.get('damaged_parts', [])),
                'Repair_Time_Estimate__c': damage_assessment.get('repair_time_estimate', '0 days'),
                'Claim_Status__c': 'New',
                'Claim_Date__c': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
            }
            
            # Create the claim
            response = self.sf.Vehicle_Claim__c.create(claim_data)
            
            if response.get('success'):
                claim_id = response.get('id')
                logger.info(f"Created claim in Salesforce with ID: {claim_id}")
                return {
                    'success': True,
                    'claim_id': claim_id,
                    'message': 'Claim created successfully'
                }
            else:
                logger.error(f"Failed to create claim: {response}")
                return {
                    'success': False,
                    'message': 'Failed to create claim in Salesforce'
                }
                
        except Exception as e:
            logger.error(f"Error creating claim in Salesforce: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}"
            }
    
    def get_available_time_slots(self, start_date=None, days=7):
        """
        Get available time slots for repair service scheduling.
        
        Args:
            start_date: Start date for time slots (defaults to tomorrow)
            days: Number of days to look ahead
            
        Returns:
            List of available time slots
        """
        if start_date is None:
            start_date = datetime.now() + timedelta(days=1)
        
        try:
            # Query Salesforce for available slots
            # This is a placeholder - actual query would depend on your Salesforce schema
            query = f"""
            SELECT Id, Date__c, Start_Time__c, End_Time__c, Available__c
            FROM Service_Time_Slot__c
            WHERE Date__c >= {start_date.strftime('%Y-%m-%d')}
            AND Date__c <= {(start_date + timedelta(days=days)).strftime('%Y-%m-%d')}
            AND Available__c = true
            ORDER BY Date__c, Start_Time__c
            """
            
            # For demo purposes, let's generate some sample time slots
            # Remove this and use the actual Salesforce query in production
            time_slots = self._generate_sample_time_slots(start_date, days)
            
            return {
                'success': True,
                'time_slots': time_slots
            }
            
        except Exception as e:
            logger.error(f"Error fetching time slots from Salesforce: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}"
            }
    
    def _generate_sample_time_slots(self, start_date, days):
        """Generate sample time slots for demo purposes."""
        time_slots = []
        current_date = start_date
        
        for _ in range(days):
            # Skip weekends
            if current_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
                current_date += timedelta(days=1)
                continue
                
            # Generate slots for each day
            for hour in [9, 11, 13, 15, 17]:
                slot = {
                    'id': f"slot_{current_date.strftime('%Y%m%d')}_{hour}",
                    'date': current_date.strftime('%Y-%m-%d'),
                    'day': current_date.strftime('%A'),
                    'start_time': f"{hour}:00",
                    'end_time': f"{hour + 1}:00",
                    'available': True
                }
                time_slots.append(slot)
            
            current_date += timedelta(days=1)
        
        return time_slots
    
    def schedule_service(self, claim_id, time_slot_id, customer_name, phone_number, email):
        """
        Schedule a service appointment.
        
        Args:
            claim_id: Salesforce claim ID
            time_slot_id: Selected time slot ID
            customer_name: Customer's name
            phone_number: Customer's phone number
            email: Customer's email
            
        Returns:
            Dictionary with appointment details
        """
        try:
            # Parse time slot information from the ID
            # Format: slot_YYYYMMDD_HH
            date_part = time_slot_id.split('_')[1]
            hour_part = time_slot_id.split('_')[2]
            
            appointment_date = datetime.strptime(date_part, '%Y%m%d')
            appointment_time = f"{hour_part}:00"
            
            # Create appointment in Salesforce
            appointment_data = {
                'Claim__c': claim_id,
                'Appointment_Date__c': appointment_date.strftime('%Y-%m-%d'),
                'Appointment_Time__c': appointment_time,
                'Customer_Name__c': customer_name,
                'Phone__c': phone_number,
                'Email__c': email,
                'Status__c': 'Scheduled'
            }
            
            # For demo purposes, we'll skip the actual Salesforce call
            # In production, you would do:
            # response = self.sf.Service_Appointment__c.create(appointment_data)
            
            return {
                'success': True,
                'appointment_id': 'appointment_12345',  # This would come from Salesforce
                'message': 'Appointment scheduled successfully',
                'details': {
                    'date': appointment_date.strftime('%Y-%m-%d'),
                    'day': appointment_date.strftime('%A'),
                    'time': appointment_time,
                    'location': '123 Auto Repair Center, Main Street',
                    'confirmation_code': 'CONF-' + ''.join([str(x) for x in range(6)])
                }
            }
            
        except Exception as e:
            logger.error(f"Error scheduling service in Salesforce: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}"
            } 