import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

# Use a different location
MODEL_PATH = './fraud_model.pkl'

# Create a very simple model
X = np.array([[0, 0, 0, 0], [1, 1, 1, 1]])
y = np.array([0, 1])

model = RandomForestClassifier(n_estimators=2, max_depth=2)
model.fit(X, y)

# Save the model
joblib.dump(model, MODEL_PATH)
print(f"Simple model saved to {os.path.abspath(MODEL_PATH)}")

# Update config path
with open('model_path.txt', 'w') as f:
    f.write(os.path.abspath(MODEL_PATH)) 