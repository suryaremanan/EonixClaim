"""
Simple test script to verify model loading.
"""
import os
import sys
import joblib

MODEL_PATH = '/home/suryaremanan/eonixclaim/models/fraud_detection.pkl'

print(f"Checking for model at: {MODEL_PATH}")
print(f"File exists: {os.path.exists(MODEL_PATH)}")
print(f"File size: {os.path.getsize(MODEL_PATH) if os.path.exists(MODEL_PATH) else 'N/A'} bytes")

try:
    print("Attempting to load model...")
    model = joblib.load(MODEL_PATH)
    print("Model loaded successfully!")
    print(f"Model type: {type(model)}")
    
    # Test with a sample prediction
    import numpy as np
    test_case = np.array([[2, 3000, 0, 2]])
    print(f"Making a test prediction...")
    prediction = model.predict(test_case)
    prob = model.predict_proba(test_case)[0][1]
    print(f"Prediction: {prediction}, Probability: {prob:.2f}")
    
except Exception as e:
    print(f"Error loading model: {e}")
    print(f"Python version: {sys.version}")
    print(f"Joblib version: {joblib.__version__}") 