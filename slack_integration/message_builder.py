"""
Slack message builder module.

This module provides utilities for building structured Slack messages and
interactive UIs for the InsurTech platform.
"""
import logging
from typing import Dict, List, Any, Optional
import json

# Configure logger
logger = logging.getLogger(__name__)

class MessageBuilder:
    """
    Build structured Slack messages.
    
    This class provides utilities for building structured Slack messages and
    interactive UIs for the InsurTech platform.
    """
    
    @staticmethod
    def build_policy_info_message(policy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build a message displaying policy information.
        
        Args:
            policy: Dictionary of policy information
            
        Returns:
            List of Slack blocks
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Policy Information"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Policy Number:*\n{policy['policy_number']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Customer:*\n{policy['customer_name']}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Vehicle VIN:*\n{policy['vehicle_vin']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\n{policy['status']}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Premium:*\n${policy['premium_amount']:.2f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Coverage Period:*\n{policy['start_date']} to {policy['end_date']}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Coverage Details:*\n{policy['coverage_details']}"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        return blocks
        
    @staticmethod
    def build_damage_detection_message(damage_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build a message displaying damage detection results.
        
        Args:
            damage_results: Dictionary of damage detection results
            
        Returns:
            List of Slack blocks
        """
        # Build damage summary
        damage_summary = "*Detected Vehicle Damage:*\n\n"
        
        for damage_type, count in damage_results['damage_summary'].items():
            damage_summary += f"• {damage_type.replace('_', ' ').title()}: {count} instance(s)\n"
            
        damage_summary += f"\nSeverity Score: {damage_results['severity_score']:.2f}/1.0"
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": damage_summary
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Submit Claim"
                        },
                        "style": "primary",
                        "action_id": "submit_claim",
                        "value": json.dumps({"damage_results": damage_results})
                    }
                ]
            }
        ]
        
        return blocks
        
    @staticmethod
    def build_claim_confirmation_message(claim_id: str, policy_number: str,
                                        claim_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build a message confirming claim submission.
        
        Args:
            claim_id: Claim ID
            policy_number: Policy number
            claim_details: Dictionary of claim details
            
        Returns:
            List of Slack blocks
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Claim Submitted Successfully"
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
                        "text": f"*Policy Number:*\n{policy_number}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Incident Date:*\n{claim_details.get('incident_date', 'Not specified')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Estimated Damage:*\n${claim_details.get('estimated_amount', 0):.2f}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:*\n{claim_details.get('description', 'No description provided')}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Confirm Claim"
                        },
                        "style": "primary",
                        "action_id": "confirm_claim",
                        "value": json.dumps({"claim_id": claim_id})
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Cancel Claim"
                        },
                        "style": "danger",
                        "action_id": "cancel_claim",
                        "value": json.dumps({"claim_id": claim_id})
                    }
                ]
            }
        ]
        
        return blocks
        
    @staticmethod
    def build_fraud_alert_message(claim_id: str, fraud_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build a message for fraud detection alerts.
        
        Args:
            claim_id: Claim ID
            fraud_result: Dictionary of fraud detection results
            
        Returns:
            List of Slack blocks
        """
        risk_factors = ""
        if fraud_result.get('risk_factors'):
            risk_factors = "\n\n*Risk Factors:*\n"
            for factor in fraud_result['risk_factors']:
                risk_factors += f"• {factor}\n"
                
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚠️ Potential Fraud Alert ⚠️",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Our system has identified potential irregularities with claim #{claim_id}. " + 
                           f"The case has been escalated to our fraud investigation team.{risk_factors}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Fraud probability: {fraud_result['fraud_probability']:.2%} | Reference #: {claim_id}"
                    }
                ]
            }
        ]
        
        return blocks
        
    @staticmethod
    def build_help_message() -> List[Dict[str, Any]]:
        """
        Build a help message describing available commands.
        
        Returns:
            List of Slack blocks
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "InsurTech Assistant Help"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Here are the ways you can interact with the InsurTech Assistant:"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Upload a photo* - Upload a photo of vehicle damage to get an instant assessment"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Type 'policy <policy_number>'* - View details of your insurance policy"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Type 'claim <claim_id>'* - Check the status of an existing claim"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Type 'help'* - Display this help message"
                }
            }
        ]
        
        return blocks 