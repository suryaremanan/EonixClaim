"""
Fraud detection module for insurance claims.

This module uses machine learning to identify potentially fraudulent insurance
claims based on claim characteristics and historical patterns.
"""
import os
import logging
import pickle
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from config.config import FRAUD_MODEL_PATH

# Configure logger
logger = logging.getLogger(__name__)

class FraudDetector:
    """
    Fraud detection for insurance claims.
    
    This class uses machine learning to identify potentially fraudulent
    insurance claims based on claim characteristics and historical patterns.
    """
    
    def __init__(self, model_path: str = FRAUD_MODEL_PATH):
        """
        Initialize the fraud detector.
        
        Args:
            model_path: Path to the trained fraud detection model
        """
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.feature_names = None
        
        # Load the model during initialization
        self._load_model()
        
    def _load_model(self) -> None:
        """Load the trained fraud detection model from disk."""
        try:
            if not os.path.exists(self.model_path):
                logger.warning(f"Fraud detection model not found at {self.model_path}")
                # In a real-world scenario, we might want to either:
                # 1. Train a new model if we have data
                # 2. Use a fallback rule-based approach
                return
                
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
                
            self.model = model_data.get('model')
            self.scaler = model_data.get('scaler')
            self.feature_names = model_data.get('feature_names')
            
            logger.info(f"Successfully loaded fraud detection model from {self.model_path}")
            
        except Exception as e:
            logger.error(f"Error loading fraud detection model: {e}")
            
    def _preprocess_claim(self, claim_data: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        Preprocess a claim for fraud detection.
        
        Args:
            claim_data: Dictionary of claim information
            
        Returns:
            Numpy array of preprocessed features or None if preprocessing fails
        """
        try:
            if not self.feature_names:
                logger.error("Feature names not available for preprocessing")
                return None
                
            # Extract features from claim data
            features = []
            
            for feature in self.feature_names:
                if feature in claim_data:
                    features.append(claim_data[feature])
                else:
                    logger.warning(f"Feature {feature} not found in claim data")
                    features.append(0.0)  # Default value
                    
            # Apply scaling if available
            if self.scaler:
                features = self.scaler.transform([features])[0]
                
            return np.array(features).reshape(1, -1)
            
        except Exception as e:
            logger.error(f"Error preprocessing claim for fraud detection: {e}")
            return None
            
    def detect_fraud(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect potential fraud in an insurance claim.
        
        Args:
            claim_data: Dictionary of claim information
            
        Returns:
            Dictionary with fraud detection results:
            {
                'fraud_probability': Probability of fraud (0.0 to 1.0),
                'is_fraudulent': Boolean indicating likely fraud,
                'confidence': Confidence score for the prediction,
                'risk_factors': List of factors contributing to fraud risk
            }
        """
        # Default response with low fraud probability
        result = {
            'fraud_probability': 0.1,
            'is_fraudulent': False,
            'confidence': 0.0,
            'risk_factors': []
        }
        
        if not self.model:
            logger.warning("Fraud detection model not available")
            return result
            
        try:
            # Preprocess the claim
            features = self._preprocess_claim(claim_data)
            
            if features is None:
                logger.error("Failed to preprocess claim for fraud detection")
                return result
                
            # Make prediction
            fraud_prob = self.model.predict_proba(features)[0, 1]
            is_fraudulent = fraud_prob >= 0.6  # Threshold for fraud classification
            
            # Get feature importances for this prediction
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
                
                # Sort features by importance
                indices = np.argsort(importances)[::-1]
                
                # Get risk factors (top 3 most important features for this prediction)
                risk_factors = []
                for i in range(min(3, len(indices))):
                    if importances[indices[i]] > 0.05:  # Only include significant factors
                        feature_name = self.feature_names[indices[i]]
                        risk_factors.append(feature_name)
            else:
                risk_factors = []
                
            result = {
                'fraud_probability': float(fraud_prob),
                'is_fraudulent': is_fraudulent,
                'confidence': 0.7 if 0.3 < fraud_prob < 0.7 else 0.9,
                'risk_factors': risk_factors
            }
            
            logger.info(f"Completed fraud detection - Probability: {fraud_prob:.4f}, Fraudulent: {is_fraudulent}")
            return result
            
        except Exception as e:
            logger.error(f"Error in fraud detection: {e}")
            return result 