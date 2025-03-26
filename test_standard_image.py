from ultralytics import YOLO
import cv2
import os

# Load model
model = YOLO("/home/suryaremanan/eonixclaim/Damaged-Car-parts-prediction-using-YOLOv8/best.pt")

# Use a standard damage image
image_path = "/home/suryaremanan/eonixclaim/test_images/11.jpg"

# Set a very low threshold
results = model(image_path, conf=0.01)

# Create the output directory first
os.makedirs("output", exist_ok=True)

# Plot the results
im_array = results[0].plot()  # Plot results
im = cv2.cvtColor(im_array, cv2.COLOR_RGB2BGR)  # Convert to BGR for cv2 saving
output_path = os.path.join("output", "annotated_" + os.path.basename(image_path))
cv2.imwrite(output_path, im)  # Save the image

print(f"Detections: {len(results[0].boxes)}")
print(f"Classes detected:")
for i, box in enumerate(results[0].boxes):
    class_id = int(box.cls[0])
    class_name = results[0].names[class_id]
    conf = float(box.conf[0])
    print(f"{i+1}. {class_name}: {conf:.4f}")
print(f"Annotated image saved to {output_path}") 