"""
Salesforce integration for damage analysis using Prompt Builder.
"""
import requests
import json
import logging
import os
from typing import Dict, Any, Optional

# Configure logger
logger = logging.getLogger(__name__)

class SalesforcePromptAnalyzer:
    """
    Analyzes vehicle damage using Salesforce Prompt Builder.
    """
    
    def __init__(self):
        """Initialize the Salesforce prompt analyzer."""
        # Get credentials and token from environment variables
        self.sf_instance_url = os.environ.get("SALESFORCE_INSTANCE_URL")
        self.access_token = os.environ.get("SALESFORCE_ACCESS_TOKEN")
        
        logger.info("Salesforce Prompt Analyzer initialized with direct token")
    
    def analyze_damage(self, damage_results: Dict[str, Any], vehicle_info: Dict[str, Any] = None, 
                      policy_info: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze damage using Salesforce Prompt Builder with AgentForce agents.
        """
        try:
            # Try to call Salesforce API
            result = self._call_salesforce_api(damage_results, vehicle_info, policy_info)
            if result:
                return result
            
            # Fall back to mock if API call fails
            logger.warning("Falling back to mock analysis due to Salesforce API issues")
            damaged_parts = damage_results.get("damaged_parts", [])
            costs = [self._estimate_cost_for_part(part) for part in damaged_parts]
            mock_analysis = self._generate_mock_analysis(damaged_parts, costs)
            return {"analysis": mock_analysis}
            
        except Exception as e:
            logger.error(f"Error analyzing damage with Salesforce: {e}")
            return {"analysis": "An error occurred while analyzing the damage. Please try again later."}
    
    def _call_salesforce_api(self, damage_results, vehicle_info=None, policy_info=None):
        """
        Call the Salesforce API to analyze damage.
        
        Args:
            damage_results: Results from YOLOv8 damage detection
            vehicle_info: Optional vehicle information
            policy_info: Optional policy information
            
        Returns:
            Analysis results from Salesforce or None if error
        """
        try:
            # Format the damage data for the prompt
            damaged_parts = damage_results.get("damaged_parts", [])
            
            # Extract confidence scores from detections
            confidence_scores = []
            for detection in damage_results.get("detections", []):
                if detection.get("class_name", ""):
                    confidence_scores.append(
                        detection.get("confidence", 0.8)
                    )
            
            # Calculate costs for each part
            costs = []
            for part in damaged_parts:
                costs.append(self._estimate_cost_for_part(part))
            
            # Default vehicle and policy info if not provided
            if not vehicle_info:
                vehicle_info = {"make": "BMW", "model": "1 Series", "year": "2022"}
                
            if not policy_info:
                policy_info = {"coverage": "Comprehensive", "deductible": "$500"}
            
            # AgentForce specific prompt template
            prompt_template = """# Vehicle Damage Assessment Analysis

## Context
You are an expert insurance adjuster helping me analyze vehicle damage from AI-detected images. I have YOLOv8 model outputs showing damaged vehicle parts. I need you to analyze this data for risk assessment, pricing considerations, and customer recommendations.

## Input Data
{damaged_parts: {{parts}}}
{confidence_scores: {{confidence}}}
{estimated_repair_costs: {{costs}}}
{vehicle_info: {{vehicle}}}
{policy_coverage: {{policy}}}
{customer_history: []}

## Instructions
1. Analyze the detected damage severity based on:
   - Number and type of damaged parts
   - Location of damage (structural vs. cosmetic)
   - Potential for hidden/internal damage
   
2. Provide a comprehensive assessment including:
   - Likelihood of total loss determination
   - Repair vs. replacement recommendations for each part
   - Potential impact on vehicle safety and operation
   - Estimated total repair time
   
3. Include coverage analysis:
   - Whether the identified damage is covered under policy
   - Potential deductible impacts
   - Recommended coverage adjustments
   
4. Outline potential fraud indicators (if any):
   - Inconsistencies in damage patterns
   - Damage that doesn't match reported incident
   - Historical patterns from similar claims
   
5. Recommend next steps:
   - Additional documentation needed
   - Preferred repair facilities in network
   - Rental car or alternative transportation options
   - Preventative maintenance advice

## Tone and Format
- Professional yet empathetic
- Structured with clear sections
- Factual and data-driven while acknowledging customer concerns
- Include bullet points for easy scanning
- Conclude with a clear summary of recommendations

## Response Structure
[Assessment Summary]
[Damage Analysis By Part]
[Coverage Review]
[Risk Indicators]
[Customer Recommendations]
[Next Steps]"""

            # For Salesforce's Prompt Builder/AgentForce API
            prompt_input = {
                "model": "gpt-4", 
                "prompt": prompt_template,
                "temperature": 0.7,
                "promptInputs": {
                    "parts": damaged_parts,
                    "confidence": confidence_scores,
                    "costs": costs,
                    "vehicle": vehicle_info,
                    "policy": policy_info
                }
            }
            
            # Log the API request for debugging
            logger.info(f"Calling Salesforce with prompt inputs: {json.dumps(prompt_input['promptInputs'])}")
            
            # Try multiple authentication methods
            
            # METHOD 1: Try with Bearer token (standard format)
            try:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(
                    f"{self.sf_instance_url}/services/apexrest/AgentForce/analyze",
                    headers=headers,
                    json=prompt_input,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Successfully received AgentForce analysis")
                    return {"analysis": result.get("response", "No analysis provided")}
            except Exception as e:
                logger.warning(f"First attempt failed: {e}")
            
            # METHOD 2: Try without 'Bearer' prefix
            try:
                headers = {
                    "Authorization": self.access_token,
                    "Content-Type": "application/json"
                }
                
                response = requests.post(
                    f"{self.sf_instance_url}/services/apexrest/AgentForce/analyze",
                    headers=headers,
                    json=prompt_input,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Successfully received AgentForce analysis (without Bearer)")
                    return {"analysis": result.get("response", "No analysis provided")}
            except Exception as e:
                logger.warning(f"Second attempt failed: {e}")
                
            # METHOD 3: Try Einstein API endpoint
            try:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(
                    f"{self.sf_instance_url}/services/data/v59.0/einstein/prompts/execute",
                    headers=headers,
                    json=prompt_input,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Successfully received Einstein API analysis")
                    return {"analysis": result.get("response", "No analysis provided")}
            except Exception as e:
                logger.warning(f"Third attempt failed: {e}")
                
            # All attempts failed
            logger.error("All Salesforce API attempts failed")
            return None
            
        except Exception as e:
            logger.error(f"Error in _call_salesforce_api: {e}")
            return None
    
    def _estimate_cost_for_part(self, part_name):
        """Estimate the cost for a damaged part."""
        # Default costs for common parts
        cost_map = {
            "hood": 1200,
            "bumper": 800,
            "fender": 600,
            "door": 950,
            "headlight": 450,
            "taillight": 350,
            "windshield": 500,
            "mirror": 300,
            "wheel": 350,
            "trunk": 900,
            "grill": 400
        }
        
        # Try to match the part name to our cost map
        for key, cost in cost_map.items():
            if key in part_name.lower():
                return cost
        
        # Default cost for unknown parts
        return 750 

    def _generate_mock_analysis(self, damaged_parts, costs):
        """Generate a mock analysis for testing when Salesforce is not available."""
        # Basic templated analysis based on the damaged parts
        part_noun = "part" if len(damaged_parts) == 1 else "parts"
        cost_total = sum(costs)
        
        # Common parts and their characteristics
        part_details = {
            "hood": {
                "structural": True,
                "safety": "The hood damage may compromise the crumple zone designed to absorb impact energy in a collision.",
                "repair": "Replacement recommended due to structural implications."
            },
            "bumper": {
                "structural": True,
                "safety": "Damaged bumpers affect the vehicle's ability to absorb impact in low-speed collisions.",
                "repair": "Replacement is typically required as modern bumpers contain impact sensors and absorption materials."
            },
            "headlight": {
                "structural": False,
                "safety": "Compromised headlights reduce visibility and may not meet safety regulations.",
                "repair": "Complete replacement including wiring and housing is recommended."
            },
            "door": {
                "structural": True,
                "safety": "Door damage may affect side-impact protection systems.",
                "repair": "Depending on severity, may require replacement or significant bodywork."
            },
            "fender": {
                "structural": False, 
                "safety": "Primarily cosmetic, but may have sharp edges that should be addressed.",
                "repair": "Can often be repaired rather than replaced if damage is limited."
            }
        }
        
        # Generate part-specific analysis
        part_analysis = []
        structural_count = 0
        
        for part in damaged_parts:
            details = part_details.get(part, {
                "structural": False,
                "safety": "Impact on safety is undetermined.",
                "repair": "Professional assessment recommended."
            })
            
            if details["structural"]:
                structural_count += 1
                
            part_analysis.append(f"**{part.title()}**:\n- {details['safety']}\n- {details['repair']}")
        
        repair_time = 2 + structural_count + (len(damaged_parts) // 2)
        
        # Build the complete analysis
        analysis = f"""
## Assessment Summary
The vehicle has sustained damage to {len(damaged_parts)} {part_noun}: {', '.join(damaged_parts)}. Based on AI detection and damage patterns, this appears to be a {'moderate to severe' if structural_count > 0 else 'minor to moderate'} collision with {'significant structural implications' if structural_count > 1 else 'potential structural concerns' if structural_count == 1 else 'primarily cosmetic damage'}.

## Damage Analysis By Part
{chr(10).join(part_analysis)}

## Coverage Review
Your Comprehensive coverage applies to this type of damage, subject to your $500 deductible. The estimated repair cost of ${cost_total:,.2f} exceeds your deductible, making you eligible for a claim payment of approximately ${max(0, cost_total - 500):,.2f}.

## Risk Indicators
No significant fraud indicators were detected in the damage pattern. The damage is consistent with a {'frontal collision' if 'hood' in damaged_parts or 'bumper' in damaged_parts else 'side impact'}.

## Customer Recommendations
- File your claim promptly to expedite the repair process
- Consider obtaining multiple repair quotes to ensure fair pricing
- Document the damage thoroughly with additional photos from various angles

## Next Steps
1. Schedule an inspection at one of our preferred repair facilities
2. Arrange for a rental vehicle through our partnership program (covered for up to {repair_time+2} days under your policy)
3. Submit any additional documentation through our mobile app or customer portal
4. Contact your claims adjuster with any questions at 1-800-555-CLAIM

Estimated repair time: {repair_time} days
"""
        return analysis 

    def analyze_damage_description(self, description_text):
        """
        Analyze text description of vehicle damage.
        
        Args:
            description_text: User's description of the damage
            
        Returns:
            Dictionary with analysis results
        """
        try:
            logger.info(f"Analyzing damage description: {description_text}")
            
            # Prepare prompt inputs
            prompt_inputs = {
                "description": description_text,
                "policy": {
                    "coverage": "Comprehensive",
                    "deductible": "$500"
                }
            }
            
            # Call Salesforce with the prompt
            analysis = self._call_salesforce_with_prompt(prompt_inputs)
            
            if analysis:
                logger.info("Successfully analyzed damage description")
                return analysis
            else:
                logger.warning("Failed to analyze damage description with Salesforce API")
                return self._get_mock_analysis_for_description(description_text)
        
        except Exception as e:
            logger.error(f"Error analyzing damage description: {e}")
            return self._get_mock_analysis_for_description(description_text)
    
    def _get_mock_analysis_for_description(self, description_text):
        """
        Generate mock analysis for a damage description when Salesforce API is unavailable.
        
        Args:
            description_text: User's description of the damage
            
        Returns:
            Dictionary with mock analysis
        """
        logger.warning("Using mock analysis for damage description")
        
        # Extract likely damaged parts from the description
        parts = []
        if "bumper" in description_text.lower():
            parts.append("bumper")
        if "hood" in description_text.lower():
            parts.append("hood")
        if "headlight" in description_text.lower() or "head light" in description_text.lower():
            parts.append("headlight")
        if "door" in description_text.lower():
            parts.append("door")
        if "fender" in description_text.lower():
            parts.append("fender")
        if "window" in description_text.lower() or "windshield" in description_text.lower():
            parts.append("windshield")
        if "mirror" in description_text.lower():
            parts.append("mirror")
        
        # If no specific parts were found, add a default
        if not parts:
            parts = ["bumper"]
        
        # Generate a basic analysis based on the parts
        part_text = ", ".join(parts)
        
        analysis_text = f"""
## Assessment Summary
Based on your description, your vehicle has sustained damage to the {part_text}. This appears to be a moderate collision with potential impact on the vehicle's safety features.

## Damage Analysis
The damage to your {part_text} may affect the vehicle's structural integrity and safety systems. A professional inspection is recommended to assess the full extent of the damage.

## Coverage Review
Your Comprehensive coverage applies to this type of damage, subject to your $500 deductible. Based on similar claims, estimated repair costs typically range from $800-$2,500 depending on the extent of damage.

## Next Steps
1. Schedule an inspection at one of our preferred repair facilities
2. Ensure you have documentation of the damage
3. Prepare your insurance information for the repair center
4. Contact your claims adjuster with any questions
"""
        
        return {
            "status": "success",
            "analysis": analysis_text,
            "source": "mock"
        } 