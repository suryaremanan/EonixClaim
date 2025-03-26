"""
Slack handler for telematics data analysis and visualization.
"""
import logging
import json
from datetime import datetime
from slack_bolt import App
from telematics.telematics_processor import TelematicsProcessor
from fraud_detection.fraud_detector import FraudDetector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize processors
telematics_processor = TelematicsProcessor()
fraud_detector = FraudDetector()

def register_handlers(app: App):
    """Register telematics analysis handlers with the Slack app."""
    
    @app.command("/analyze-driver")
    def handle_analyze_driver(ack, command, client, logger):
        """Handle slack command to analyze a driver's telematics data."""
        # Acknowledge the command request immediately
        ack()
        
        try:
            # Extract driver ID from command text
            driver_id = command["text"].strip()
            if not driver_id:
                client.chat_postMessage(
                    channel=command["channel_id"],
                    text="Please provide a driver ID. Example: `/analyze-driver 12345`"
                )
                return
                
            # Send initial response
            client.chat_postMessage(
                channel=command["channel_id"],
                text=f"Analyzing telematics data for driver {driver_id}..."
            )
            
            # Analyze driver behavior
            analysis = telematics_processor.analyze_driver_behavior(driver_id)
            
            if "error" in analysis:
                client.chat_postMessage(
                    channel=command["channel_id"],
                    text=f"Error: {analysis['error']}"
                )
                return
                
            # Format response
            metrics = analysis["metrics"]
            scores = analysis["scores"]
            risk_level = analysis["risk_level"]
            risk_score = analysis["risk_score"]
            
            # Determine emoji based on risk level
            if risk_level == "High":
                risk_emoji = "🔴"
            elif risk_level == "Medium":
                risk_emoji = "🟠"
            else:
                risk_emoji = "🟢"
                
            # Create blocks for rich message
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Driver {driver_id} Telematics Analysis",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Risk Assessment:* {risk_emoji} {risk_level} Risk (Score: {risk_score}/100)"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Speed Score:* {scores['speed_score']}/100"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Acceleration Score:* {scores['acceleration_score']}/100"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Braking Score:* {scores['braking_score']}/100"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Cornering Score:* {scores['cornering_score']}/100"
                        }
                    ]
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Driving Metrics*"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Avg Speed:* {metrics['avg_speed']} km/h"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Max Speed:* {metrics['max_speed']} km/h"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Harsh Accelerations:* {metrics['harsh_acceleration_count']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Harsh Brakings:* {metrics['harsh_braking_count']}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Harsh Cornerings:* {metrics['harsh_cornering_count']}"
                        },
                        {
                            "type": "mrkdwn", 
                            "text": f"*Anomalies Detected:* {metrics['anomaly_count']}"
                        }
                    ]
                }
            ]
            
            # Add a button for detailed analysis
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Check for Fraud Indicators",
                            "emoji": True
                        },
                        "value": f"{driver_id}",
                        "action_id": "check_fraud_indicators"
                    }
                ]
            })
            
            # Send the message
            client.chat_postMessage(
                channel=command["channel_id"],
                blocks=blocks,
                text=f"Driver {driver_id} Analysis: {risk_level} Risk (Score: {risk_score}/100)"
            )
            
        except Exception as e:
            logger.error(f"Error handling analyze-driver command: {e}")
            client.chat_postMessage(
                channel=command["channel_id"],
                text=f"An error occurred while analyzing telematics data: {str(e)}"
            )
    
    @app.action("check_fraud_indicators")
    def handle_check_fraud(ack, body, client, logger):
        """Handle button click to check fraud indicators."""
        # Acknowledge the action immediately
        ack()
        
        try:
            # Extract driver ID
            driver_id = body["actions"][0]["value"]
            channel_id = body["channel"]["id"]
            
            # Create a mock damage assessment (in reality, this would come from previous processing)
            mock_assessment = {
                "damaged_parts": ["hood", "bumper"],
                "estimated_repair_cost": 1800,
                "severity": "Moderate"
            }
            
            # Mock incident time (this would come from claim details)
            incident_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get telematics data around the incident
            telematics_data = telematics_processor.check_driving_behavior_near_incident(
                driver_id, incident_time
            )
            
            # Mock claim history (this would come from your database)
            mock_history = [
                {
                    "date": datetime(2023, 6, 15),
                    "damaged_parts": ["rear_bumper", "tail_light"],
                    "cost": 1200
                },
                {
                    "date": datetime(2022, 11, 3),
                    "damaged_parts": ["door", "window"],
                    "cost": 1800
                }
            ]
            
            # Evaluate fraud probability
            fraud_result = fraud_detector.evaluate_claim(
                mock_assessment, telematics_data, mock_history, incident_time
            )
            
            # Format response
            fraud_prob = fraud_result["fraud_probability"]
            fraud_rating = fraud_result["fraud_rating"]
            fraud_flags = fraud_result["fraud_flags"]
            
            # Determine emoji based on fraud rating
            if fraud_rating == "High":
                fraud_emoji = "⚠️"
            elif fraud_rating == "Medium":
                fraud_emoji = "⚠"
            else:
                fraud_emoji = "✅"
                
            # Create message blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Fraud Analysis for Driver {driver_id}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Fraud Rating:* {fraud_emoji} {fraud_rating} ({fraud_prob * 100:.0f}%)"
                    }
                }
            ]
            
            # Add telematics incident information
            incident_blocks = []
            if "error" in telematics_data:
                incident_blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"⚠️ *Telematics Error:* {telematics_data['error']}"
                    }
                })
            elif telematics_data.get("has_incident_indicators", False):
                incident_emoji = "✅"
                incident_text = "*Telematics confirms incident*\n"
                if telematics_data.get("sudden_stop_detected"):
                    incident_text += "• Sudden stop detected\n"
                if telematics_data.get("sudden_swerve_detected"):
                    incident_text += "• Sudden swerve detected\n"
                if telematics_data.get("significant_speed_change"):
                    incident_text += "• Significant speed change detected\n"
                    
                if "impact_time" in telematics_data:
                    incident_text += f"• Impact time: {telematics_data['impact_time']}\n"
                    incident_text += f"• Impact speed: {telematics_data['impact_speed']} km/h\n"
                    
                if telematics_data.get("time_mismatch"):
                    incident_text += f"⚠️ *Warning:* Reported time differs from detected impact by {telematics_data['time_difference_minutes']} minutes\n"
            else:
                incident_emoji = "❌"
                incident_text = "*No incident indicators in telematics data*\n"
                incident_text += "The telematics data does not show evidence of an incident at the reported time.\n"
                
            incident_blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{incident_emoji} {incident_text}"
                }
            })
            
            blocks.extend(incident_blocks)
            
            # Add fraud flags section if any exist
            if fraud_flags:
                flags_text = "*Fraud Indicators:*\n"
                for flag in fraud_flags:
                    readable_flag = flag.replace("_", " ").title()
                    flags_text += f"• {readable_flag}\n"
                    
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": flags_text
                    }
                })
                
            # Add recommendation based on fraud rating
            if fraud_rating == "High":
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{fraud_result.get('message', '⚠️ *Recommendation:* This claim requires investigation before proceeding.')}"
                    }
                })
            elif fraud_rating == "Medium":
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "⚠ *Recommendation:* Additional documentation may be required for this claim."
                    }
                })
            else:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "✅ *Recommendation:* This claim shows no significant fraud indicators and can be processed normally."
                    }
                })
                
            # Send the message
            client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text=f"Fraud Analysis: {fraud_rating} Risk"
            )
            
        except Exception as e:
            logger.error(f"Error handling check fraud indicators: {e}")
            client.chat_postMessage(
                channel=channel_id,
                text="Error message"
            ) 