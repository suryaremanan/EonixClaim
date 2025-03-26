"""
YOLO-based vehicle damage detection module.

This module implements vehicle damage detection using YOLOv8 to identify and
classify different types of vehicle damage from images.
"""
import os
import logging
from typing import Dict, List, Tuple, Any, Optional
import torch
from PIL import Image
import numpy as np
from ultralytics import YOLO

from config.config import YOLO_MODEL_PATH, YOLO_CONFIDENCE_THRESHOLD, DAMAGE_CLASSES

# Configure logger
logger = logging.getLogger(__name__)

class VehicleDamageDetector:
    """
    Detects and classifies vehicle damage using YOLOv8.
    
    This class loads a pre-trained YOLOv8 model and uses it to detect
    various types of vehicle damage in images.
    """
    
    def __init__(self, model_path: str = YOLO_MODEL_PATH, 
                 confidence_threshold: float = YOLO_CONFIDENCE_THRESHOLD):
        """
        Initialize the vehicle damage detector.
        
        Args:
            model_path: Path to the YOLOv8 model file
            confidence_threshold: Minimum confidence score for detections
        """
        self.confidence_threshold = confidence_threshold
        
        # Load the YOLO model
        try:
            self.model = YOLO(model_path)
            logger.info(f"Successfully loaded YOLO model from {model_path}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
            
        # Set device (GPU if available, otherwise CPU)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"Using device: {self.device}")
        
    def detect_damage(self, image_path: str) -> Dict[str, Any]:
        """
        Detect vehicle damage in an image.
        
        Args:
            image_path: Path to the image file to analyze
            
        Returns:
            Dictionary containing detection results:
            {
                'detections': List of detection dictionaries with class, confidence, and bounding box,
                'damage_summary': Summary of detected damage types and counts,
                'image_path': Path to the annotated image output
            }
        """
        if not os.path.exists(image_path):
            logger.error(f"Image not found: {image_path}")
            raise FileNotFoundError(f"Image not found: {image_path}")
            
        try:
            # Run inference
            logger.info(f"Running damage detection on {image_path}")
            results = self.model(image_path)[0]
            
            # Process results
            detections = []
            damage_count = {damage_type: 0 for damage_type in DAMAGE_CLASSES}
            
            for detection in results.boxes.data.tolist():
                x1, y1, x2, y2, confidence, class_id = detection
                
                if confidence < self.confidence_threshold:
                    continue
                    
                class_id = int(class_id)
                class_name = self.model.names[class_id]
                
                # Only process if the class is a damage type we're interested in
                if class_name in DAMAGE_CLASSES:
                    detections.append({
                        'class': class_name,
                        'confidence': float(confidence),
                        'bbox': [float(x1), float(y1), float(x2), float(y2)]
                    })
                    damage_count[class_name] += 1
            
            # Create annotated image
            annotated_img = results.plot()
            output_path = f"{os.path.splitext(image_path)[0]}_annotated.jpg"
            Image.fromarray(annotated_img).save(output_path)
            
            return {
                'detections': detections,
                'damage_summary': {k: v for k, v in damage_count.items() if v > 0},
                'image_path': output_path,
                'severity_score': self._calculate_severity_score(damage_count)
            }
            
        except Exception as e:
            logger.error(f"Error detecting damage in image {image_path}: {e}")
            raise
    
    def _calculate_severity_score(self, damage_count: Dict[str, int]) -> float:
        """
        Calculate a severity score based on detected damage.
        
        Args:
            damage_count: Dictionary of damage types and their counts
            
        Returns:
            Severity score from 0.0 to 1.0
        """
        # Define weights for different damage types
        damage_weights = {
            'dent': 0.3,
            'scratch': 0.2,
            'broken_glass': 0.8,
            'broken_light': 0.5,
            'tire_damage': 0.7
        }
        
        # Calculate weighted sum of damage
        weighted_sum = sum(damage_count[damage] * damage_weights.get(damage, 0.0) 
                           for damage in damage_count)
        
        # Normalize to 0-1 range (assuming max reasonable score is 5.0)
        severity = min(weighted_sum / 5.0, 1.0)
        
        return round(severity, 2) 