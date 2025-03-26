"""
Vehicle damage detection module using YOLOv8 model.
"""
import os
import logging
import cv2
import numpy as np
from ultralytics import YOLO
from config.config import YOLO_MODEL_PATH, YOLO_CONFIDENCE_THRESHOLD, DAMAGE_CLASSES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VehicleDamageDetector:
    """
    Vehicle damage detection using YOLO model.
    Detects damaged vehicle parts directly.
    """
    
    def __init__(self):
        """Initialize vehicle damage detector with YOLOv8 model."""
        # Check model path
        if not YOLO_MODEL_PATH or not os.path.exists(YOLO_MODEL_PATH):
            logger.error(f"YOLO model not found at: {YOLO_MODEL_PATH}")
            raise FileNotFoundError(f"YOLO model not found at: {YOLO_MODEL_PATH}")
            
        logger.info(f"Loading YOLOv8 model from: {YOLO_MODEL_PATH}")
        self.model = YOLO(YOLO_MODEL_PATH)
        self.confidence_threshold = YOLO_CONFIDENCE_THRESHOLD
        
        # Use damage classes from config
        self.damage_classes = DAMAGE_CLASSES
        
        logger.info(f"Vehicle damage detector initialized with {len(self.damage_classes)} damage classes")
    
    def detect_objects(self, image_path):
        """
        Detect damaged vehicle parts in an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with detection results
        """
        if not os.path.exists(image_path):
            logger.error(f"Image not found: {image_path}")
            return {"error": "Image not found"}
        
        try:
            # Read the image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to read image: {image_path}")
                return {"error": "Failed to read image"}
            
            # Run YOLO detection
            results = self.model(image)
            
            # Process results
            detections = []
            damages = []
            damage_types = set()
            annotated_image = image.copy()
            
            # Extract detections
            for result in results:
                boxes = result.boxes.cpu().numpy()
                for i, box in enumerate(boxes):
                    # Use a very low threshold for debugging
                    if box.conf[0] < 0.01:
                        continue
                    
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].astype(int)
                    
                    # Get class
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    confidence = float(box.conf[0])
                    
                    # Store detection
                    detection = {
                        'class_id': class_id,
                        'class_name': class_name,
                        'confidence': confidence,
                        'box': [x1, y1, x2, y2]
                    }
                    detections.append(detection)
                    
                    # All detections are damage
                    damages.append(class_name)
                    damage_types.add(class_name)
                    
                    # Draw bounding box on the image
                    cv2.rectangle(annotated_image, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(annotated_image, f"{class_name} {confidence:.2f}", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # Save annotated image
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            output_filename = os.path.join(output_dir, f"annotated_{os.path.basename(image_path)}")

            # Get the annotated image from the results object
            im_array = results[0].plot()  # Plot results with boxes
            im = cv2.cvtColor(im_array, cv2.COLOR_RGB2BGR)  # Convert from RGB to BGR format
            cv2.imwrite(output_filename, im)  # Save the image
            
            # Extract damaged parts from the damage class names
            damaged_parts = self._extract_parts_from_damage(damages)
            
            return {
                "status": "success",
                "detections": detections,
                "damages": list(damage_types),
                "damaged_parts": damaged_parts,
                "annotated_image": output_filename
            }
            
        except Exception as e:
            logger.error(f"Error during detection: {e}", exc_info=True)
            return {"error": f"Detection failed: {str(e)}"}
    
    def _extract_parts_from_damage(self, damages):
        """
        Extract the part names from damage class names.
        E.g., 'damaged door' -> 'door'
        """
        parts = set()
        for damage in damages:
            if damage == 'dent':
                continue  # Skip 'dent' as it doesn't specify a part
            
            # Extract part name by removing 'damaged ' prefix
            if damage.startswith('damaged '):
                part = damage[8:]  # Remove 'damaged ' prefix
                parts.add(part)
        
        return list(parts)
    
    def get_damage_assessment(self, image_path):
        """
        Get a comprehensive damage assessment for a vehicle image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with damage assessment results
        """
        # Get detections
        detection_results = self.detect_objects(image_path)
        
        if "error" in detection_results:
            return detection_results
        
        # Process damage assessment
        damaged_parts = detection_results["damaged_parts"]
        damages = detection_results["damages"]
        total_damage_detected = len(detection_results["damages"])
        
        # Calculate estimated repair costs
        part_repair_costs = {
            'door': {'min': 750, 'max': 2000, 'avg': 1100},
            'window': {'min': 250, 'max': 800, 'avg': 450},
            'headlight': {'min': 250, 'max': 1500, 'avg': 600},
            'mirror': {'min': 200, 'max': 900, 'avg': 400},
            'hood': {'min': 500, 'max': 1500, 'avg': 800},
            'bumper': {'min': 600, 'max': 1500, 'avg': 950},
            'wind shield': {'min': 250, 'max': 1200, 'avg': 600}
        }
        
        # Default values for parts not in the dictionary
        default_repair_cost = {'min': 200, 'max': 1000, 'avg': 500}
        
        # Calculate estimated repair cost
        estimated_cost = 0
        for part in damaged_parts:
            part_cost = part_repair_costs.get(part, default_repair_cost)
            estimated_cost += part_cost['avg']
        
        # Add cost for each dent detected
        dent_count = damages.count('dent')
        dent_cost = 300  # Average cost to repair a dent
        estimated_cost += dent_count * dent_cost
        
        # If no specific damaged parts but dents were detected
        if not damaged_parts and dent_count > 0:
            estimated_cost = dent_count * dent_cost
        
        # Determine damage severity
        if len(damaged_parts) == 0 and dent_count == 0:
            severity = "None"
            estimated_cost = 0
        elif (len(damaged_parts) <= 1 and dent_count <= 1) or estimated_cost < 1000:
            severity = "Minor"
        elif (len(damaged_parts) <= 3 and dent_count <= 3) or estimated_cost < 3000:
            severity = "Moderate"
        else:
            severity = "Severe"
        
        # Return assessment results
        return {
            "status": "success",
            "vehicle_parts": [],  # Not applicable with this model
            "damages": detection_results["damages"],
            "damaged_parts": damaged_parts,
            "total_damage_detected": total_damage_detected,
            "severity": severity,
            "estimated_repair_cost": estimated_cost,
            "annotated_image": detection_results.get("annotated_image"),
            "repair_time_estimate": f"{max(1, len(damaged_parts) * 1.5):.1f} days"
        } 