"""Test the YOLOv8 vehicle parts and damage detector."""
import os
from image_processing.vehicle_parts_detector import VehicleDamageDetector

def test_detector():
    """Test the vehicle damage detector with new class labels."""
    detector = VehicleDamageDetector()
    
    # Test image path - update this to a real image path
    test_image = "/home/suryaremanan/eonixclaim/test_images/11.jpg"
    
    if not os.path.exists(test_image):
        print(f"Test image not found: {test_image}")
        return
    
    result = detector.get_damage_assessment(test_image)
    print("Detection result:")
    print(f"Status: {result.get('status')}")
    print(f"Vehicle Parts Detected: {result.get('vehicle_parts')}")
    print(f"Damage Types Detected: {result.get('damages')}")
    print(f"Damaged Parts: {result.get('damaged_parts')}")
    print(f"Severity: {result.get('severity')}")
    print(f"Estimated repair cost: ${result.get('estimated_repair_cost')}")
    print(f"Repair time estimate: {result.get('repair_time_estimate')}")
    print(f"Annotated image saved to: {result.get('annotated_image')}")

if __name__ == "__main__":
    test_detector() 