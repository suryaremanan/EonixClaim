"""
Fraud detection module for insurance claims.
Analyzes damage assessments, telematics data, and historical patterns.
"""
import os
import logging
import numpy as np
import joblib
from datetime import datetime
from config.config import FRAUD_MODEL_PATH, FRAUD_DETECTION_MESSAGE
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Try to read custom model path
    if os.path.exists('model_path.txt'):
        with open('model_path.txt', 'r') as f:
            CUSTOM_MODEL_PATH = f.read().strip()
        if os.path.exists(CUSTOM_MODEL_PATH):
            logger.info(f"Using custom model path: {CUSTOM_MODEL_PATH}")
            FRAUD_MODEL_PATH = CUSTOM_MODEL_PATH
except:
    pass

class FraudDetector:
    """
    Fraud detection system for insurance claims.
    Uses multiple data sources to detect potential fraud.
    """
    
    def __init__(self):
        """Initialize fraud detector."""
        self.fraud_model = None
        self.load_model()
        logger.info("Fraud detector initialized in demo mode (rule-based detection)")
        
    def load_model(self):
        """Load the fraud detection model."""
        try:
            model_path = FRAUD_MODEL_PATH
            if os.path.exists(model_path):
                try:
                    logger.info(f"Attempting to load fraud model from: {model_path}")
                    self.fraud_model = joblib.load(model_path)
                    logger.info("Fraud detection model loaded successfully!")
                except Exception as e:
                    logger.error(f"Could not load fraud model: {str(e)}")
                    logger.error("Model-based fraud detection unavailable")
                    self.fraud_model = None
            else:
                logger.error(f"Fraud model not found at {model_path}")
                logger.error("Model-based fraud detection unavailable")
                self.fraud_model = None
        except Exception as e:
            logger.error(f"Issue checking for fraud model: {e}")
            self.fraud_model = None
    
    def _evaluate_damage_consistency(self, damage_assessment):
        """
        Evaluate internal consistency of damage assessment.
        
        Returns:
            Tuple of (score, flags) where score is 0-1 (higher means more consistent)
            and flags is a list of specific inconsistencies.
        """
        flags = []
        
        # Check if detected damages are consistent with repair cost
        damaged_parts = damage_assessment.get("damaged_parts", [])
        estimated_cost = damage_assessment.get("estimated_repair_cost", 0)
        
        # Rough estimate: each damaged part should contribute $400-$1000 on average
        expected_min_cost = len(damaged_parts) * 400
        expected_max_cost = len(damaged_parts) * 1200
        
        if damaged_parts and estimated_cost < expected_min_cost * 0.5:
            flags.append("cost_too_low")
        if damaged_parts and estimated_cost > expected_max_cost * 1.5:
            flags.append("cost_too_high")
            
        # Calculate consistency score
        if not flags:
            return 1.0, flags
        else:
            return 0.7, flags
    
    def evaluate_claim(self, damage_assessment, telematics_data=None, claim_history=None, incident_time=None):
        """
        Evaluate a claim for potential fraud.
        
        Args:
            damage_assessment: Dictionary with damage assessment results
            telematics_data: Dictionary with telematics analysis (optional)
            claim_history: List of previous claims (optional)
            incident_time: Reported time of incident (optional)
            
        Returns:
            Dictionary with fraud evaluation results
        """
        try:
            # Start with a baseline fraud probability
            fraud_probability = 0.05
            fraud_flags = []
            
            # 1. Check internal consistency of damage assessment
            damage_consistency, damage_flags = self._evaluate_damage_consistency(damage_assessment)
            if damage_consistency < 0.8:
                fraud_probability += 0.2
                fraud_flags.extend(damage_flags)
            
            # 2. Check telematics data if available
            if telematics_data and incident_time:
                # No incident indicators in telematics
                if not telematics_data.get("has_incident_indicators", True):
                    fraud_probability += 0.4
                    fraud_flags.append("no_telematics_incident")
                
                # Time mismatch between reported and detected
                if telematics_data.get("time_mismatch", False):
                    fraud_probability += 0.25
                    fraud_flags.append("time_mismatch")
            
            # 3. Check claim history if available
            if claim_history:
                # Count recent claims (last 12 months)
                recent_claim_count = sum(1 for claim in claim_history 
                                         if (datetime.now() - claim["date"]).days <= 365)
                
                # Multiple recent claims are suspicious
                if recent_claim_count >= 3:
                    fraud_probability += 0.2
                    fraud_flags.append("multiple_recent_claims")
                    
                # Check for similar damage patterns
                similar_damages = 0
                current_damages = set(damage_assessment.get("damaged_parts", []))
                for claim in claim_history:
                    past_damages = set(claim.get("damaged_parts", []))
                    if len(current_damages.intersection(past_damages)) >= 2:
                        similar_damages += 1
                
                if similar_damages >= 2:
                    fraud_probability += 0.15
                    fraud_flags.append("repeated_damage_pattern")
            
            # 4. Use ML model if available
            if self.fraud_model:
                # Extract and normalize features for the model
                # This would need to be customized based on your model's expected input
                try:
                    # Example features:
                    features = [
                        len(damage_assessment.get("damaged_parts", [])),
                        damage_assessment.get("estimated_repair_cost", 0) / 1000,
                        1 if telematics_data and telematics_data.get("has_incident_indicators", False) else 0,
                        recent_claim_count if claim_history else 0
                    ]
                    
                    # Make prediction
                    model_fraud_prob = self.fraud_model.predict_proba([features])[0][1]
                    
                    # Blend rule-based and model predictions
                    fraud_probability = 0.6 * fraud_probability + 0.4 * model_fraud_prob
                    
                except Exception as e:
                    logger.error(f"Error using fraud model: {e}")
            
            # 5. Determine final fraud assessment
            fraud_rating = "Low"
            if fraud_probability >= 0.7:
                fraud_rating = "High"
            elif fraud_probability >= 0.4:
                fraud_rating = "Medium"
                
            # Create result
            result = {
                "fraud_probability": round(fraud_probability, 2),
                "fraud_rating": fraud_rating,
                "fraud_flags": fraud_flags,
                "requires_investigation": fraud_probability >= 0.4
            }
            
            # Add custom message for high fraud probability
            if fraud_probability >= 0.7:
                result["message"] = FRAUD_DETECTION_MESSAGE.format(claim_id="CL-" + datetime.now().strftime("%Y%m%d%H%M"))
            
            return result
            
        except Exception as e:
            logger.error(f"Error in fraud evaluation: {e}")
            return {
                "error": f"Fraud evaluation error: {str(e)}",
                "fraud_rating": "Unknown",
                "requires_investigation": True
            }

    def check_image(self, image_path: str, damage_results: Dict[str, Any]) -> float:
        """
        Check an image for signs of fraud.
        
        Args:
            image_path: Path to the image file
            damage_results: Results from damage detection
            
        Returns:
            Fraud score (0.0 to 1.0, higher means more likely fraudulent)
        """
        logger.info(f"Checking image for fraud indicators: {image_path}")
        
        # Debug - log the actual format we're receiving
        logger.info(f"Damage results type: {type(damage_results)}")
        logger.info(f"Damage results content: {damage_results}")
        
        # Handle string input (convert to dict if possible)
        if isinstance(damage_results, str):
            try:
                import json
                damage_results = json.loads(damage_results)
            except:
                logger.warning("Could not parse string damage results as JSON")
                # Return a moderate fraud score 
                return 0.35
        
        # Use the existing evaluate_risk method if it exists
        if hasattr(self, 'evaluate_risk'):
            return self.evaluate_risk(damage_results)
        
        try:
            # More parts claimed as damaged = slightly higher risk
            if isinstance(damage_results, dict) and "damaged_parts" in damage_results:
                damaged_parts = damage_results.get("damaged_parts", [])
            elif isinstance(damage_results, list):
                # If it's already a list of parts
                damaged_parts = damage_results
            else:
                # If we can't determine the structure, use an empty list
                damaged_parts = []
            
            num_parts = len(damaged_parts)
            parts_score = min(num_parts / 10, 0.5)  # Max 0.5 for many parts
            
            # Higher damage claimed = slightly higher risk
            total_cost = 0
            if isinstance(damaged_parts, list):
                for part in damaged_parts:
                    if isinstance(part, dict):
                        total_cost += part.get("estimated_cost", 0)
                
            cost_score = min(total_cost / 10000, 0.3)  # Max 0.3 for high cost
            
            # Usually low confidence = higher risk
            confidence_scores = []
            if isinstance(damaged_parts, list):
                for part in damaged_parts:
                    if isinstance(part, dict) and "confidence" in part:
                        confidence_scores.append(part.get("confidence", 0.9))
                    
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.9
            confidence_score = max(0, 0.2 * (1 - avg_confidence))  # Max 0.2 for low confidence
            
            # Calculate final score
            fraud_score = parts_score + cost_score + confidence_score
            
            # Add a small random factor
            import random
            fraud_score += random.uniform(-0.05, 0.05)
            
            # Clamp between 0 and 1
            fraud_score = max(0.0, min(fraud_score, 1.0))
            
            logger.info(f"Calculated fraud score: {fraud_score:.2f}")
            return fraud_score
            
        except Exception as e:
            logger.error(f"Error calculating fraud score: {e}")
            # Return a moderate fraud score in case of errors
            return 0.35 