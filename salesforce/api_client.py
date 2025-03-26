"""
Salesforce API client module.

This module provides integration with Salesforce for retrieving and 
updating insurance policy and claim information.
"""
import logging
from typing import Dict, List, Any, Optional
import json

from simple_salesforce import Salesforce
from requests.exceptions import ConnectionError, Timeout, RequestException

from config.config import SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN, SF_DOMAIN

# Configure logger
logger = logging.getLogger(__name__)

class SalesforceClient:
    """
    Salesforce API client for insurance operations.
    
    This class handles authentication and API operations with Salesforce
    for policy management, claim processing, and customer data.
    """
    
    def __init__(self, username: str = SF_USERNAME, 
                 password: str = SF_PASSWORD,
                 security_token: str = SF_SECURITY_TOKEN,
                 domain: str = SF_DOMAIN):
        """
        Initialize the Salesforce client.
        
        Args:
            username: Salesforce username
            password: Salesforce password
            security_token: Salesforce security token
            domain: Salesforce instance domain
        """
        self.username = username
        self.password = password
        self.security_token = security_token
        self.domain = domain
        self.client = None
        
        # Validate credentials
        if not all([username, password, security_token]):
            logger.warning("Salesforce credentials not fully provided")
            
    def connect(self) -> bool:
        """
        Connect to Salesforce.
        
        Returns:
            True if connection successful, False otherwise
        """
        if self.client is not None:
            return True
            
        try:
            self.client = Salesforce(
                username=self.username,
                password=self.password,
                security_token=self.security_token,
                domain=self.domain
            )
            logger.info("Successfully connected to Salesforce")
            return True
            
        except ConnectionError as e:
            logger.error(f"Connection error to Salesforce: {e}")
        except Timeout as e:
            logger.error(f"Timeout connecting to Salesforce: {e}")
        except Exception as e:
            logger.error(f"Error connecting to Salesforce: {e}")
            
        return False
        
    def get_policy(self, policy_number: str) -> Optional[Dict[str, Any]]:
        """
        Get policy information from Salesforce.
        
        Args:
            policy_number: Insurance policy number
            
        Returns:
            Dictionary of policy information or None if not found
        """
        if not self.connect():
            return None
            
        try:
            # Query policy from Salesforce
            query = f"SELECT Id, Name, PolicyNumber__c, CustomerName__c, VehicleVIN__c, Status__c, PremiumAmount__c, StartDate__c, EndDate__c FROM InsurancePolicy__c WHERE PolicyNumber__c = '{policy_number}'"
            
            result = self.client.query(query)
            
            if result['totalSize'] == 0:
                logger.warning(f"Policy not found: {policy_number}")
                return None
                
            policy_record = result['records'][0]
            
            # Convert Salesforce record to dict
            policy = {
                'id': policy_record['Id'],
                'policy_number': policy_record['PolicyNumber__c'],
                'customer_name': policy_record['CustomerName__c'],
                'vehicle_vin': policy_record['VehicleVIN__c'],
                'status': policy_record['Status__c'],
                'premium_amount': policy_record['PremiumAmount__c'],
                'start_date': policy_record['StartDate__c'],
                'end_date': policy_record['EndDate__c']
            }
            
            logger.info(f"Retrieved policy information for {policy_number}")
            return policy
            
        except Exception as e:
            logger.error(f"Error retrieving policy {policy_number}: {e}")
            return None
    
    def create_claim(self, claim_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new insurance claim in Salesforce.
        
        Args:
            claim_data: Dictionary containing claim information
            
        Returns:
            Claim ID if successful, None otherwise
        """
        if not self.connect():
            return None
            
        try:
            # Prepare claim record
            claim_record = {
                'PolicyId__c': claim_data.get('policy_id'),
                'ClaimDate__c': claim_data.get('claim_date'),
                'Description__c': claim_data.get('description'),
                'DamageType__c': claim_data.get('damage_type'),
                'EstimatedAmount__c': claim_data.get('estimated_amount'),
                'Status__c': 'New'
            }
            
            # Create claim in Salesforce
            result = self.client.InsuranceClaim__c.create(claim_record)
            
            if result.get('success'):
                claim_id = result.get('id')
                logger.info(f"Created new claim with ID: {claim_id}")
                
                # If we have damage images, attach them to the claim
                if 'damage_images' in claim_data:
                    self._attach_images_to_claim(claim_id, claim_data['damage_images'])
                    
                return claim_id
            else:
                logger.error(f"Failed to create claim: {result.get('errors')}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating claim: {e}")
            return None
            
    def update_claim_status(self, claim_id: str, status: str, 
                            notes: Optional[str] = None) -> bool:
        """
        Update the status of an existing claim.
        
        Args:
            claim_id: ID of the claim to update
            status: New status value
            notes: Optional notes about the status change
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connect():
            return False
            
        try:
            # Prepare update data
            update_data = {'Status__c': status}
            
            if notes:
                update_data['Notes__c'] = notes
                
            # Update claim in Salesforce
            self.client.InsuranceClaim__c.update(claim_id, update_data)
            
            logger.info(f"Updated claim {claim_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating claim {claim_id}: {e}")
            return False
    
    def _attach_images_to_claim(self, claim_id: str, image_paths: List[str]) -> None:
        """
        Attach damage images to a claim.
        
        Args:
            claim_id: ID of the claim
            image_paths: List of paths to damage images
        """
        if not self.connect():
            return
            
        try:
            for image_path in image_paths:
                filename = image_path.split('/')[-1]
                
                with open(image_path, 'rb') as file:
                    file_content = file.read()
                    
                    # Create ContentVersion
                    content_data = {
                        'Title': f"Damage Image - {filename}",
                        'PathOnClient': filename,
                        'VersionData': file_content.encode('base64'),
                        'FirstPublishLocationId': claim_id
                    }
                    
                    self.client.ContentVersion.create(content_data)
                    
            logger.info(f"Attached {len(image_paths)} images to claim {claim_id}")
            
        except Exception as e:
            logger.error(f"Error attaching images to claim {claim_id}: {e}") 