"""Direct test of the vehicle damage detector."""
import os
from image_processing.vehicle_parts_detector import VehicleDamageDetector

# Initialize the detector
detector = VehicleDamageDetector()

# Test with a specific image path - update this to a real image on your system
test_image = "/home/suryaremanan/eonixclaim/test_images/11.jpg"

if not os.path.exists(test_image):
    print(f"Test image not found: {test_image}")
    exit(1)

# Run detection
print(f"Testing detection on: {test_image}")
result = detector.get_damage_assessment(test_image)
print("Detection result:")
print(f"Status: {result.get('status')}")
print(f"Damaged parts: {result.get('damaged_parts')}")
print(f"Severity: {result.get('severity')}")
print(f"Estimated repair cost: ${result.get('estimated_repair_cost')}")
print(f"Repair time estimate: {result.get('repair_time_estimate')}")
print(f"Annotated image saved to: {result.get('annotated_image')}") 