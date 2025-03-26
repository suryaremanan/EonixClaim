"""
Risk assessment module for telematics data.

This module evaluates driving risk based on telematics data and generates
risk scores for insurance pricing and policy decisions.
"""
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from config.config import RISK_THRESHOLD_HIGH, RISK_THRESHOLD_MEDIUM

# Configure logger
logger = logging.getLogger(__name__)

class RiskAssessor:
    """
    Assess driving risk based on telematics data.
    
    This class evaluates driving risk and generates risk scores for
    insurance pricing and policy decisions.
    """
    
    def __init__(self, high_risk_threshold: float = RISK_THRESHOLD_HIGH,
                 medium_risk_threshold: float = RISK_THRESHOLD_MEDIUM):
        """
        Initialize the risk assessor.
        
        Args:
            high_risk_threshold: Threshold for high risk classification
            medium_risk_threshold: Threshold for medium risk classification
        """
        self.high_risk_threshold = high_risk_threshold
        self.medium_risk_threshold = medium_risk_threshold
        logger.info(f"Initialized RiskAssessor with thresholds - high: {high_risk_threshold}, medium: {medium_risk_threshold}")
        
    def calculate_risk_score(self, behavior_metrics: Dict[str, Any]) -> float:
        """
        Calculate a risk score based on driver behavior metrics.
        
        Args:
            behavior_metrics: Dictionary of driver behavior metrics
            
        Returns:
            Risk score from 0.0 (lowest risk) to 1.0 (highest risk)
        """
        try:
            # Define weights for different metrics
            weights = {
                'harsh_braking_pct': 0.2,
                'rapid_accel_pct': 0.15,
                'speeding_pct': 0.3,
                'high_jerk_pct': 0.1,
                'engine_stress_pct': 0.05,
                'overall_driving_score': -0.2  # Negative weight as higher score is better
            }
            
            # Initialize risk score
            risk_score = 0.0
            
            # Add weighted contributions from each metric
            for metric, weight in weights.items():
                if metric in behavior_metrics:
                    value = behavior_metrics[metric]
                    
                    # For overall_driving_score, convert from 0-100 scale to 0-1 scale and invert
                    if metric == 'overall_driving_score':
                        value = 1.0 - (value / 100.0)
                    else:
                        # For percentage metrics, convert to 0-1 scale
                        value = value / 100.0
                    
                    risk_score += value * weight
            
            # Normalize to 0-1 range
            risk_score = max(0.0, min(1.0, risk_score))
            
            logger.info(f"Calculated risk score: {risk_score:.4f}")
            return risk_score
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            raise
    
    def get_risk_category(self, risk_score: float) -> str:
        """
        Get the risk category based on the risk score.
        
        Args:
            risk_score: Risk score from 0.0 to 1.0
            
        Returns:
            Risk category string ('low', 'medium', or 'high')
        """
        if risk_score >= self.high_risk_threshold:
            return 'high'
        elif risk_score >= self.medium_risk_threshold:
            return 'medium'
        else:
            return 'low'
            
    def calculate_premium_adjustment(self, risk_score: float) -> float:
        """
        Calculate premium adjustment factor based on risk score.
        
        Args:
            risk_score: Risk score from 0.0 to 1.0
            
        Returns:
            Premium adjustment factor (1.0 = no change, >1.0 = increase, <1.0 = decrease)
        """
        # Define adjustment formula: 
        # - Low risk (0.0-0.3): 10-30% discount
        # - Medium risk (0.3-0.7): -10% to +20% adjustment
        # - High risk (0.7-1.0): 20-100% premium increase
        
        if risk_score < self.medium_risk_threshold:
            # Low risk: 10-30% discount
            return 0.9 - (0.2 * (self.medium_risk_threshold - risk_score) / self.medium_risk_threshold)
        elif risk_score < self.high_risk_threshold:
            # Medium risk: -10% to +20% adjustment
            normalized_score = (risk_score - self.medium_risk_threshold) / (self.high_risk_threshold - self.medium_risk_threshold)
            return 0.9 + (0.3 * normalized_score)
        else:
            # High risk: 20-100% premium increase
            normalized_score = (risk_score - self.high_risk_threshold) / (1.0 - self.high_risk_threshold)
            return 1.2 + (0.8 * normalized_score)
            
    def generate_risk_report(self, behavior_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive risk report.
        
        Args:
            behavior_metrics: Dictionary of driver behavior metrics
            
        Returns:
            Dictionary containing risk assessment results
        """
        try:
            # Calculate risk score
            risk_score = self.calculate_risk_score(behavior_metrics)
            
            # Determine risk category
            risk_category = self.get_risk_category(risk_score)
            
            # Calculate premium adjustment
            premium_adjustment = self.calculate_premium_adjustment(risk_score)
            
            # Generate risk factors list
            risk_factors = []
            
            if behavior_metrics.get('harsh_braking_pct', 0) > 5:
                risk_factors.append("Frequent harsh braking")
                
            if behavior_metrics.get('rapid_accel_pct', 0) > 5:
                risk_factors.append("Frequent rapid acceleration")
                
            if behavior_metrics.get('speeding_pct', 0) > 10:
                risk_factors.append("Frequent speeding")
                
            if behavior_metrics.get('high_jerk_pct', 0) > 3:
                risk_factors.append("Erratic driving patterns")
                
            if behavior_metrics.get('engine_stress_pct', 0) > 15:
                risk_factors.append("Engine stress from improper gear usage")
                
            # Build report
            report = {
                'risk_score': risk_score,
                'risk_category': risk_category,
                'premium_adjustment_factor': premium_adjustment,
                'premium_change_pct': (premium_adjustment - 1.0) * 100,
                'risk_factors': risk_factors,
                'driving_metrics': {
                    'smoothness_score': behavior_metrics.get('smoothness_score', 0),
                    'speed_management_score': behavior_metrics.get('speed_management_score', 0),
                    'overall_driving_score': behavior_metrics.get('overall_driving_score', 0)
                }
            }
            
            logger.info(f"Generated risk report for driver - Category: {risk_category}, Score: {risk_score:.4f}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating risk report: {e}")
            raise 