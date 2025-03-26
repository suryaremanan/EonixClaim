"""
Telematics data processing module.

This module processes and analyzes vehicle telemetry data for driving behavior
analysis and risk assessment.
"""
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

from config.config import TELEMATICS_DATA_PATH

# Configure logger
logger = logging.getLogger(__name__)

class TelematicsProcessor:
    """
    Process and analyze vehicle telematics data.
    
    This class provides methods to load, clean, and analyze telematics data
    for driving behavior analysis and risk assessment.
    """
    
    def __init__(self, data_path: str = TELEMATICS_DATA_PATH):
        """
        Initialize the telematics processor.
        
        Args:
            data_path: Path to the directory containing telematics data files
        """
        self.data_path = data_path
        logger.info(f"Initialized TelematicsProcessor with data path: {data_path}")
        
    def load_data(self, vehicle_id: str, date_range: Optional[Tuple[str, str]] = None) -> pd.DataFrame:
        """
        Load telematics data for a specific vehicle.
        
        Args:
            vehicle_id: Unique identifier for the vehicle
            date_range: Optional tuple of (start_date, end_date) as strings in YYYY-MM-DD format
            
        Returns:
            DataFrame containing the telematics data
        """
        try:
            # Construct file path
            file_path = os.path.join(self.data_path, f"{vehicle_id}.csv")
            
            if not os.path.exists(file_path):
                logger.error(f"Telematics data file not found: {file_path}")
                raise FileNotFoundError(f"Telematics data not found for vehicle ID: {vehicle_id}")
                
            # Load the data
            df = pd.read_csv(file_path, parse_dates=['timestamp'])
            logger.info(f"Loaded telematics data for vehicle {vehicle_id}: {len(df)} records")
            
            # Filter by date range if provided
            if date_range:
                start_date, end_date = date_range
                df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
                logger.info(f"Filtered data to date range {start_date} to {end_date}: {len(df)} records")
                
            return df
            
        except Exception as e:
            logger.error(f"Error loading telematics data for vehicle {vehicle_id}: {e}")
            raise
            
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and preprocess telematics data.
        
        Args:
            df: DataFrame containing raw telematics data
            
        Returns:
            Cleaned DataFrame
        """
        try:
            # Make a copy to avoid modifying the original
            cleaned_df = df.copy()
            
            # Sort by timestamp
            cleaned_df = cleaned_df.sort_values('timestamp')
            
            # Drop duplicates
            initial_count = len(cleaned_df)
            cleaned_df = cleaned_df.drop_duplicates()
            if len(cleaned_df) < initial_count:
                logger.info(f"Removed {initial_count - len(cleaned_df)} duplicate records")
                
            # Handle missing values
            for col in cleaned_df.columns:
                missing = cleaned_df[col].isna().sum()
                if missing > 0:
                    if col in ['speed', 'rpm', 'fuel_level', 'throttle_position']:
                        # For critical numeric columns, interpolate missing values
                        cleaned_df[col] = cleaned_df[col].interpolate(method='linear')
                        logger.info(f"Interpolated {missing} missing values in column '{col}'")
                    else:
                        # For other columns, forward-fill
                        cleaned_df[col] = cleaned_df[col].ffill().bfill()
                        logger.info(f"Forward/backward filled {missing} missing values in column '{col}'")
            
            # Remove outliers for numeric columns
            numeric_cols = ['speed', 'rpm', 'fuel_level', 'throttle_position', 
                           'engine_temperature', 'battery_voltage']
            for col in numeric_cols:
                if col in cleaned_df.columns:
                    # Calculate IQR
                    Q1 = cleaned_df[col].quantile(0.25)
                    Q3 = cleaned_df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    
                    # Define outlier bounds
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    
                    # Count outliers
                    outliers = ((cleaned_df[col] < lower_bound) | (cleaned_df[col] > upper_bound)).sum()
                    
                    if outliers > 0:
                        # Cap outliers
                        cleaned_df[col] = cleaned_df[col].clip(lower=lower_bound, upper=upper_bound)
                        logger.info(f"Capped {outliers} outliers in column '{col}'")
            
            return cleaned_df
            
        except Exception as e:
            logger.error(f"Error cleaning telematics data: {e}")
            raise
    
    def get_summary_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate summary statistics from telematics data.
        
        Args:
            df: DataFrame containing cleaned telematics data
            
        Returns:
            Dictionary of summary statistics
        """
        try:
            stats = {}
            
            # Basic statistics for key metrics
            if 'speed' in df.columns:
                stats['speed'] = {
                    'avg': df['speed'].mean(),
                    'max': df['speed'].max(),
                    'percentile_85': df['speed'].quantile(0.85),
                    'excessive_speed_pct': (df['speed'] > 80).mean() * 100  # Assuming 80 mph is excessive
                }
                
            if 'rpm' in df.columns:
                stats['rpm'] = {
                    'avg': df['rpm'].mean(),
                    'max': df['rpm'].max(),
                    'high_rpm_pct': (df['rpm'] > 3500).mean() * 100  # Assuming 3500 rpm is high
                }
                
            # Calculate time and distance if possible
            if 'timestamp' in df.columns:
                time_diff = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600  # in hours
                stats['duration_hours'] = time_diff
                
                if 'speed' in df.columns and time_diff > 0:
                    # Estimate distance using speed and time
                    # Convert mph to miles per unit of time between records
                    df['time_diff'] = df['timestamp'].diff().dt.total_seconds() / 3600  # in hours
                    df['segment_distance'] = df['speed'] * df['time_diff']
                    stats['estimated_distance_miles'] = df['segment_distance'].sum()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error generating summary statistics: {e}")
            raise 