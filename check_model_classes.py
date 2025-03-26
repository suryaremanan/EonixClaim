from ultralytics import YOLO

# Load model
model = YOLO("/home/suryaremanan/eonixclaim/Damaged-Car-parts-prediction-using-YOLOv8/best.pt")

# Print model info
print("Model Information:")
print(f"Task: {model.task}")
print(f"Stride: {model.stride}")

# Print class names
print("\nClass Names in Model:")
for idx, class_name in model.names.items():
    print(f"{idx}: {class_name}")

# Compare with our configuration
from config.config import VEHICLE_PART_CLASSES, DAMAGE_CLASSES
print("\nClasses defined in config:")
print(f"Vehicle parts ({len(VEHICLE_PART_CLASSES)}): {VEHICLE_PART_CLASSES}")
print(f"Damage types ({len(DAMAGE_CLASSES)}): {DAMAGE_CLASSES}")

# Check for mismatches
model_classes = set(model.names.values())
config_classes = set(VEHICLE_PART_CLASSES + DAMAGE_CLASSES)
print("\nClasses in model but not in config:")
print(model_classes - config_classes)
print("\nClasses in config but not in model:")
print(config_classes - model_classes) 