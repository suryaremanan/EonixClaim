"""
Salesforce data synchronization module.

This module provides functionality to synchronize data between the InsurTech
platform and Salesforce, including updating policies based on risk assessments.
"""
import logging
from typing import Dict, List, Any, Optional
import datetime
import json

from salesforce.api_client import SalesforceClient
from salesforce.agentforce import AgentforceManager

# Configure logger
logger = logging.getLogger(__name__)

class SalesforceSync:
    """
    Synchronize data between the InsurTech platform and Salesforce.
    
    This class handles bi-directional data flow between the InsurTech platform
    and Salesforce, including updating policies based on risk assessments.
    """
    
    def __init__(self, salesforce_client: Optional[SalesforceClient] = None,
                agentforce_manager: Optional[AgentforceManager] = None):
        """
        Initialize the Salesforce synchronization manager.
        
        Args:
            salesforce_client: Optional SalesforceClient instance
            agentforce_manager: Optional AgentforceManager instance
        """
        self.sf_client = salesforce_client or SalesforceClient()
        self.agentforce = agentforce_manager or AgentforceManager(self.sf_client)
        logger.info("Initialized Salesforce data synchronization manager")
        
    def sync_risk_assessment(self, policy_number: str, 
                            risk_report: Dict[str, Any]) -> bool:
        """
        Synchronize risk assessment results to Salesforce.
        
        Args:
            policy_number: Insurance policy number
            risk_report: Risk assessment report from the risk assessor
            
        Returns:
            True if sync was successful, False otherwise
        """
        try:
            # Get policy information from Salesforce
            policy = self.sf_client.get_policy(policy_number)
            
            if not policy:
                logger.error(f"Cannot sync risk assessment - policy not found: {policy_number}")
                return False
                
            # Update policy risk status in Salesforce
            policy_data = {
                'risk_score': risk_report['risk_score'],
                'risk_category': risk_report['risk_category'],
                'premium_adjustment_factor': risk_report['premium_adjustment_factor'],
                'risk_factors': '; '.join(risk_report['risk_factors']),
                'last_assessment_date': datetime.datetime.now().isoformat()
            }
            
            updated = self.sf_client.update_policy(policy['id'], policy_data)
            
            if not updated:
                logger.error(f"Failed to update policy {policy_number} with risk assessment")
                return False
                
            # Trigger Agentforce policy update agent
            self.agentforce.trigger_policy_update_agent(policy_number, risk_report)
            
            # Notify the customer if premium is changing significantly
            if abs(risk_report['premium_change_pct']) > 5:
                change_direction = "increase" if risk_report['premium_change_pct'] > 0 else "decrease"
                notification_data = {
                    'premiumChangePct': risk_report['premium_change_pct'],
                    'changeDirection': change_direction,
                    'effectiveDate': (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat(),
                    'riskFactors': risk_report['risk_factors']
                }
                
                self.agentforce.trigger_customer_notification_agent(
                    policy_number, 
                    policy['customer_id'],
                    'premium_adjustment',
                    notification_data
                )
                
            logger.info(f"Successfully synced risk assessment for policy {policy_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing risk assessment for policy {policy_number}: {e}")
            return False
            
    def sync_damage_assessment(self, policy_number: str, 
                              damage_report: Dict[str, Any]) -> Optional[str]:
        """
        Synchronize vehicle damage assessment to Salesforce.
        
        Args:
            policy_number: Insurance policy number
            damage_report: Damage assessment from YOLO detector
            
        Returns:
            Claim ID if successful, None otherwise
        """
        try:
            # Get policy information from Salesforce
            policy = self.sf_client.get_policy(policy_number)
            
            if not policy:
                logger.error(f"Cannot sync damage assessment - policy not found: {policy_number}")
                return None
                
            # Prepare claim data
            damage_types = list(damage_report['damage_summary'].keys())
            damage_description = f"Detected damage: {', '.join(damage_types)}"
            
            claim_data = {
                'policy_id': policy['id'],
                'claim_date': datetime.datetime.now().isoformat(),
                'description': damage_description,
                'damage_type': ', '.join(damage_types),
                'estimated_amount': 500.0 * damage_report['severity_score'],  # Simple estimation
                'damage_images': [damage_report['image_path']]
            }
            
            # Create claim in Salesforce
            claim_id = self.sf_client.create_claim(claim_data)
            
            if not claim_id:
                logger.error(f"Failed to create claim for policy {policy_number}")
                return None
            
            # Trigger Agentforce claim processing agent
            self.agentforce.trigger_claim_processing_agent(claim_id, damage_report)
            
            # Notify the customer about the new claim
            notification_data = {
                'claimId': claim_id,
                'damageDescription': damage_description,
                'estimatedAmount': 500.0 * damage_report['severity_score'],
                'nextSteps': 'Our claims team will review your claim shortly.'
            }
            
            self.agentforce.trigger_customer_notification_agent(
                policy_number,
                policy['customer_id'],
                'claim_created',
                notification_data
            )
                
            logger.info(f"Successfully created claim {claim_id} for policy {policy_number}")
            return claim_id
            
        except Exception as e:
            logger.error(f"Error syncing damage assessment for policy {policy_number}: {e}")
            return None 