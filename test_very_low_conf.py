import cv2
from ultralytics import YOLO
import numpy as np
import os

# Load model
model_path = "/home/suryaremanan/Downloads/yolo11/fastapi/models/damage_detection/best.pt"
model = YOLO(model_path)

# Test image - use the exact same image you're uploading to Slack
image_path = "/home/suryaremanan/eonixclaim/temp/F08J66RPE06_b19a4f6ecaaeb3548c4269525657b9d4.jpg"
if not os.path.exists(image_path):
    # Try a different test image
    image_path = "/home/suryaremanan/eonixclaim/test_images/11.jpg"

# Try with extremely low confidence
confidence = 0.01  # Extremely low threshold

# Read image
image = cv2.imread(image_path)
if image is None:
    print(f"Error: Cannot read image {image_path}")
    exit(1)

print(f"Testing image: {image_path}")
print(f"Image dimensions: {image.shape}")

# Run detection with very low threshold
results = model(image, conf=confidence)

# Check results
print(f"Found {len(results[0].boxes)} objects with confidence threshold {confidence}")

# Print any detections
boxes = results[0].boxes.cpu().numpy()
for i, box in enumerate(boxes):
    class_id = int(box.cls[0])
    class_name = results[0].names[class_id]
    conf = float(box.conf[0])
    x1, y1, x2, y2 = box.xyxy[0].astype(int)
    print(f"{i+1}. {class_name}: {conf:.4f} at [{x1}, {y1}, {x2}, {y2}]")

# Save annotated image
results[0].save(save_dir="output")
print(f"Annotated image saved to output folder") 