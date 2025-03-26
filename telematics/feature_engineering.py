"""
Feature engineering for telematics data.

This module creates derived features from raw telematics data for risk assessment
and driver behavior analysis.
"""
import logging
from typing import Dict, List, Any
import pandas as pd
import numpy as np

# Configure logger
logger = logging.getLogger(__name__)

class TelematicsFeatureEngineer:
    """
    Generate advanced features from telematics data.
    
    This class creates derived metrics and behavioral indicators from
    raw telematics data for use in risk assessment and driver profiling.
    """
    
    def __init__(self):
        """Initialize the telematics feature engineer."""
        logger.info("Initialized TelematicsFeatureEngineer")
        
    def add_acceleration_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add acceleration and deceleration features to the DataFrame.
        
        Args:
            df: DataFrame containing telematics data with 'speed' and 'timestamp'
            
        Returns:
            DataFrame with added acceleration features
        """
        try:
            # Make a copy to avoid modifying the original
            result_df = df.copy()
            
            # Ensure data is sorted by timestamp
            result_df = result_df.sort_values('timestamp')
            
            # Calculate time difference in seconds
            result_df['time_diff'] = result_df['timestamp'].diff().dt.total_seconds()
            
            # Calculate speed difference
            result_df['speed_diff'] = result_df['speed'].diff()
            
            # Calculate acceleration (mph/s)
            # Filter out invalid time differences
            mask = result_df['time_diff'] > 0
            result_df.loc[mask, 'acceleration'] = result_df.loc[mask, 'speed_diff'] / result_df.loc[mask, 'time_diff']
            
            # Fill NaN values with 0
            result_df['acceleration'] = result_df['acceleration'].fillna(0)
            
            # Categorize as acceleration, deceleration, or constant speed
            result_df['accel_type'] = pd.cut(
                result_df['acceleration'],
                bins=[-float('inf'), -3, -0.5, 0.5, 3, float('inf')],
                labels=['harsh_braking', 'moderate_braking', 'constant', 'moderate_acceleration', 'harsh_acceleration']
            )
            
            logger.info("Added acceleration features to telematics data")
            return result_df
            
        except Exception as e:
            logger.error(f"Error adding acceleration features: {e}")
            raise
            
    def add_driver_behavior_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add driver behavior features to the DataFrame.
        
        Args:
            df: DataFrame containing telematics data with acceleration features
            
        Returns:
            DataFrame with added driver behavior features
        """
        try:
            # Make a copy to avoid modifying the original
            result_df = df.copy()
            
            # If acceleration features aren't already added, add them
            if 'acceleration' not in result_df.columns:
                result_df = self.add_acceleration_features(result_df)
            
            # Calculate jerk (rate of change of acceleration)
            result_df['jerk'] = result_df['acceleration'].diff() / result_df['time_diff']
            result_df['jerk'] = result_df['jerk'].fillna(0)
            
            # Calculate high jerk events (sudden changes in acceleration)
            result_df['is_high_jerk'] = np.abs(result_df['jerk']) > 2.0  # Threshold for high jerk
            
            # Calculate speeding events
            result_df['is_speeding'] = result_df['speed'] > 75  # Threshold for speeding (75 mph)
            
            # Calculate rapid acceleration events
            result_df['is_rapid_accel'] = result_df['acceleration'] > 3.0  # Threshold for rapid acceleration
            
            # Calculate harsh braking events
            result_df['is_harsh_braking'] = result_df['acceleration'] < -3.0  # Threshold for harsh braking
            
            # Calculate engine stress (high RPM relative to speed)
            if 'rpm' in result_df.columns and 'speed' in result_df.columns:
                # Avoid division by zero
                mask = result_df['speed'] > 0
                result_df.loc[mask, 'rpm_speed_ratio'] = result_df.loc[mask, 'rpm'] / result_df.loc[mask, 'speed']
                result_df['rpm_speed_ratio'] = result_df['rpm_speed_ratio'].fillna(0)
                result_df['is_engine_stress'] = result_df['rpm_speed_ratio'] > 100  # Threshold for engine stress
            
            logger.info("Added driver behavior features to telematics data")
            return result_df
            
        except Exception as e:
            logger.error(f"Error adding driver behavior features: {e}")
            raise
            
    def calculate_behavior_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate aggregate metrics for driver behavior.
        
        Args:
            df: DataFrame containing telematics data with driver behavior features
            
        Returns:
            Dictionary of driver behavior metrics
        """
        try:
            metrics = {}
            
            # Ensure driver behavior features are added
            if 'is_harsh_braking' not in df.columns:
                df = self.add_driver_behavior_features(df)
            
            # Calculate percentages of different events
            total_records = len(df)
            if total_records > 0:
                metrics['harsh_braking_pct'] = df['is_harsh_braking'].mean() * 100
                metrics['rapid_accel_pct'] = df['is_rapid_accel'].mean() * 100
                metrics['speeding_pct'] = df['is_speeding'].mean() * 100
                metrics['high_jerk_pct'] = df['is_high_jerk'].mean() * 100
                
                if 'is_engine_stress' in df.columns:
                    metrics['engine_stress_pct'] = df['is_engine_stress'].mean() * 100
            
            # Calculate driving smoothness score (0-100, higher is better)
            harsh_events_pct = (
                metrics.get('harsh_braking_pct', 0) +
                metrics.get('rapid_accel_pct', 0) +
                metrics.get('high_jerk_pct', 0)
            ) / 3
            metrics['smoothness_score'] = max(0, 100 - harsh_events_pct)
            
            # Calculate speed management score (0-100, higher is better)
            speed_score = 100 - metrics.get('speeding_pct', 0)
            metrics['speed_management_score'] = max(0, speed_score)
            
            # Calculate overall driving score (0-100, higher is better)
            metrics['overall_driving_score'] = (
                metrics['smoothness_score'] * 0.6 +
                metrics['speed_management_score'] * 0.4
            )
            
            logger.info("Calculated driver behavior metrics")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating behavior metrics: {e}")
            raise 