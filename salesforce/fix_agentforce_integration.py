"""
Salesforce integration package for the InsurTech platform.
""" 

def _simulate_einstein_gpt_response(self, damage_report):
    """
    Simulate an Einstein GPT response locally.
    """
    # Extract data from damage report
    damaged_parts = damage_report.get('damaged_parts', [])
    severity = damage_report.get('severity', 'Minor')
    repair_cost = damage_report.get('estimated_repair_cost', 0)
    
    # Create formatted blocks similar to what Einstein would return
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "AI-Enhanced Damage Analysis"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*I've analyzed the damage to your vehicle and found:*\\n\\n" +
                       f"The damage appears to be {severity.lower()} in nature, affecting " +
                       f"the {', '.join(damaged_parts)}. This type of damage is typically " +
                       f"caused by a frontal collision or impact."
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Repair Details:*\\n• Estimated cost: ${repair_cost:.2f}\\n" +
                       f"• Estimated time: {max(2, len(damaged_parts) * 1.5):.1f} days\\n" +
                       f"• Recommended service: Certified collision center"
            }
        }
    ]
    
    # Add next steps
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*Next Steps:*\n" +
                    "1. We'll review your claim within 24 hours\n" +
                    "2. A claims adjuster will contact you to confirm details\n" +
                    "3. You can schedule repairs at your convenience using the button below"
        }
    })
    
    # Add Schedule Repair button
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Schedule Repair"
                },
                "style": "primary",
                "value": "schedule_repair_12345",
                "action_id": "schedule_repair"
            }
        ]
    })
    
    return blocks 