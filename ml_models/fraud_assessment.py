"""
Module for assessing potential fraud in vehicle damage claims.
"""
import logging
import os
import joblib
import numpy as np
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FraudAssessment:
    """
    Assesses potential fraud in vehicle damage claims using ML model.
    """
    
    def __init__(self):
        """Initialize fraud assessment with trained model."""
        load_dotenv()
        
        # Load fraud detection model
        model_path = os.getenv('FRAUD_MODEL_PATH')
        if not model_path or not os.path.exists(model_path):
            logger.error(f"Fraud detection model not found at: {model_path}")
            raise FileNotFoundError(f"Fraud detection model not found at: {model_path}")
        
        try:
            logger.info(f"Loading fraud detection model from: {model_path}")
            self.model_package = joblib.load(model_path)
            self.model = self.model_package['model']
            self.scaler = self.model_package['scaler']
            self.feature_names = self.model_package['feature_names']
            
            logger.info(f"Fraud detection model loaded with features: {self.feature_names}")
        except Exception as e:
            logger.error(f"Error loading fraud detection model: {str(e)}")
            raise
    
    def assess_claim(self, telematics_data, damage_assessment):
        """
        Assess potential fraud in a claim using telematics data and damage assessment.
        
        Args:
            telematics_data: Dictionary with telematics data from vehicle
            damage_assessment: Dictionary with damage assessment results
            
        Returns:
            Dictionary with fraud assessment results
        """
        try:
            # Extract features from telematics data
            features = []
            for feature_name in self.feature_names:
                if feature_name == 'data_variability':
                    # Calculate variability for the first 10 features
                    first_10_features = [telematics_data.get(f, 0) for f in list(telematics_data.keys())[:10]]
                    variability = np.std(first_10_features)
                    features.append(variability)
                else:
                    features.append(telematics_data.get(feature_name, 0))
            
            # Reshape and scale features
            features = np.array(features).reshape(1, -1)
            features_scaled = self.scaler.transform(features)
            
            # Get prediction and probability
            fraud_prediction = self.model.predict(features_scaled)[0]
            fraud_probability = self.model.predict_proba(features_scaled)[0][1]  # Probability of class 1 (fraud)
            
            # Evaluate assessment factors
            damage_severity = damage_assessment.get('severity', 'Minor')
            estimated_cost = damage_assessment.get('estimated_repair_cost', 0)
            damaged_parts = damage_assessment.get('damaged_parts', [])
            
            # Define suspicious patterns
            suspicious_factors = []
            
            # Check for inconsistencies
            if damage_severity == 'Severe' and len(damaged_parts) < 3:
                suspicious_factors.append("Severe damage claimed but few damaged parts detected")
            
            if estimated_cost > 5000 and damage_severity == 'Minor':
                suspicious_factors.append("High cost estimate but minor damage severity")
            
            # Combine ML prediction with rule-based factors
            if fraud_prediction == 1 or fraud_probability > 0.7 or len(suspicious_factors) >= 2:
                fraud_risk = "High"
            elif fraud_probability > 0.4 or len(suspicious_factors) == 1:
                fraud_risk = "Medium"
            else:
                fraud_risk = "Low"
            
            return {
                "fraud_risk": fraud_risk,
                "fraud_probability": float(fraud_probability),
                "suspicious_factors": suspicious_factors,
                "requires_investigation": fraud_risk in ["Medium", "High"],
                "ml_prediction": int(fraud_prediction)
            }
            
        except Exception as e:
            logger.error(f"Error during fraud assessment: {str(e)}")
            return {
                "error": str(e),
                "fraud_risk": "Unknown",
                "requires_investigation": True
            } 