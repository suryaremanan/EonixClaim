"""
Create a valid fraud detection model and save it to the specified path.
"""
import os
import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib

# Define the output path
MODEL_PATH = '/home/suryaremanan/eonixclaim/models/fraud_detection.pkl'

# Create directory if it doesn't exist
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

print(f"Creating fraud detection model at: {MODEL_PATH}")

# Create training data
X = np.array([
    # Features: [damaged_parts_count, repair_cost, telematics_incident, recent_claims]
    [1, 500, 1, 0],   # Not fraud
    [2, 1200, 1, 0],  # Not fraud
    [1, 3000, 0, 1],  # Fraud
    [3, 6000, 1, 0],  # Not fraud
    [2, 5000, 0, 2],  # Fraud
    [4, 2000, 1, 0],  # Not fraud
    [1, 4000, 0, 3],  # Fraud
])

y = np.array([0, 0, 1, 0, 1, 0, 1])  # 0 = Not fraud, 1 = Fraud

# Train a simple random forest model
model = RandomForestClassifier(n_estimators=10, random_state=42)
model.fit(X, y)

# Save the model using joblib (more reliable than pickle)
joblib.dump(model, MODEL_PATH)
print(f"Model saved successfully to {MODEL_PATH}")

# Test that we can load it
loaded_model = joblib.load(MODEL_PATH)
print("Model loaded successfully!")

# Test prediction
test_case = np.array([[2, 3000, 0, 2]])  # Suspicious case
fraud_prob = loaded_model.predict_proba(test_case)[0][1]
print(f"Test prediction - Fraud probability: {fraud_prob:.2f}") 