"""
Create a dummy fraud model file for development and testing.
"""
import os
import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from config.config import FRAUD_MODEL_PATH

# Create models directory if it doesn't exist
os.makedirs(os.path.dirname(FRAUD_MODEL_PATH), exist_ok=True)

# Create a simple dummy model
X = np.array([[0, 0, 0, 0], [1, 1, 1, 1]])
y = np.array([0, 1])

# Train a small random forest
model = RandomForestClassifier(n_estimators=2, max_depth=2)
model.fit(X, y)

# Save the model
with open(FRAUD_MODEL_PATH, 'wb') as f:
    pickle.dump(model, f)

print(f"Dummy fraud detection model created at {FRAUD_MODEL_PATH}") 