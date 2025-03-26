"""
Module for syncing vehicle damage assessments with Salesforce/Agentforce.
"""
import logging
from datetime import datetime
from simple_salesforce import Salesforce
from dotenv import load_dotenv
import os
import json

from image_processing.vehicle_parts_detector import VehiclePartsDetector
from salesforce.agentforce import AgentforceClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DamageAssessmentSync:
    """Handles syncing damage assessment data to Salesforce."""
    
    def __init__(self):
        """Initialize the damage assessment sync module."""
        load_dotenv()
        
        # Initialize Salesforce connection
        self.sf = Salesforce(
            username=os.getenv('SALESFORCE_USERNAME'),
            password=os.getenv('SALESFORCE_PASSWORD'),
            security_token=os.getenv('SALESFORCE_TOKEN')
        )
        
        # Initialize Agentforce client
        self.agentforce = AgentforceClient()
        
        # Initialize vehicle parts detector
        self.parts_detector = VehiclePartsDetector()
        
        logger.info("DamageAssessmentSync initialized")
    
    def process_damage_claim(self, image_path, policy_number, customer_id=None):
        """
        Process a damage claim from an image and sync to Salesforce.
        
        Args:
            image_path: Path to the vehicle damage image
            policy_number: Insurance policy number
            customer_id: Optional customer ID
            
        Returns:
            Dictionary with claim process results
        """
        try:
            # Get damage assessment
            assessment = self.parts_detector.get_damage_assessment(image_path)
            
            if "error" in assessment:
                logger.error(f"Error assessing damage: {assessment['error']}")
                return {"error": assessment["error"]}
            
            # Find policy in Salesforce
            policy_query = f"SELECT Id, Name, AccountId, Status__c FROM Insurance_Policy__c WHERE Policy_Number__c = '{policy_number}'"
            policy_results = self.sf.query(policy_query)
            
            if policy_results['totalSize'] == 0:
                return {"error": f"Policy {policy_number} not found"}
            
            policy = policy_results['records'][0]
            
            # Prepare claim data for Salesforce
            claim_data = {
                'Policy__c': policy['Id'],
                'Account__c': policy['AccountId'],
                'Damage_Severity__c': assessment['severity'],
                'Estimated_Repair_Cost__c': assessment['estimated_repair_cost'],
                'Damaged_Parts__c': ', '.join(assessment['damaged_parts']),
                'Claim_Status__c': 'New',
                'Claim_Date__c': datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                'Estimated_Repair_Time__c': assessment['repair_time_estimate']
            }
            
            # Create claim in Salesforce
            claim_result = self.sf.Insurance_Claim__c.create(claim_data)
            
            if not claim_result['success']:
                logger.error(f"Failed to create claim in Salesforce: {claim_result}")
                return {"error": "Failed to create claim in Salesforce"}
            
            claim_id = claim_result['id']
            logger.info(f"Claim created in Salesforce with ID: {claim_id}")
            
            # Run fraud detection on the claim
            fraud_detection_result = self.agentforce.trigger_fraud_detection_agent(
                policy_number=policy_number,
                claim_id=claim_id,
                damage_assessment=assessment
            )
            
            # Trigger customer notification
            notification_result = self.agentforce.trigger_customer_notification_agent(
                policy_number=policy_number,
                claim_id=claim_id,
                damage_assessment=assessment
            )
            
            # Upload annotated image to Salesforce
            if "annotated_image" in assessment and os.path.exists(assessment["annotated_image"]):
                with open(assessment["annotated_image"], 'rb') as img_file:
                    img_data = img_file.read()
                
                # Create ContentVersion
                content_data = {
                    'Title': f'Damage Assessment - {policy_number}',
                    'PathOnClient': os.path.basename(assessment["annotated_image"]),
                    'VersionData': img_data,
                    'FirstPublishLocationId': claim_id
                }
                
                content_result = self.sf.ContentVersion.create(content_data)
                
                if not content_result['success']:
                    logger.warning(f"Failed to upload image to Salesforce: {content_result}")
            
            return {
                "status": "success",
                "claim_id": claim_id,
                "assessment": assessment,
                "fraud_detection": fraud_detection_result,
                "notification": notification_result
            }
            
        except Exception as e:
            logger.error(f"Error processing damage claim: {str(e)}")
            return {"error": str(e)} 