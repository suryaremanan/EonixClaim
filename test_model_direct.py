import os
import cv2
from ultralytics import YOLO

# Load your model
model_path = "/home/suryaremanan/Downloads/yolo11/fastapi/models/damage_detection/best.pt"
model = YOLO(model_path)

# Lower confidence threshold for testing
confidence = 0.15

# Test image
test_image = "/home/suryaremanan/eonixclaim/test_images/11.jpg"

# Run inference
results = model(test_image, conf=confidence)

# Print result details
print(f"Model path: {model_path}")
print(f"Testing image: {test_image}")

# Check detection results
for r in results:
    print(f"Found {len(r.boxes)} objects")
    print(f"Class names: {r.names}")
    
    # Print each detection
    boxes = r.boxes.cpu().numpy()
    for i, box in enumerate(boxes):
        class_id = int(box.cls[0])
        class_name = r.names[class_id]
        confidence = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].astype(int)
        print(f"  {i+1}. {class_name}: {confidence:.2f} at [{x1}, {y1}, {x2}, {y2}]")

# Save annotated image
results_with_boxes = model(test_image, conf=confidence, save=True)
print(f"Annotated image saved at: {model.predictor.save_dir}") 