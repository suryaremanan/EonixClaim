import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import os

# Create directory for models if it doesn't exist
os.makedirs("models", exist_ok=True)

# Load real telematics data
print("Loading telematics data...")
data = pd.read_csv('data/telematics/data_cleaned.csv', header=0)

# Examine first few rows to understand the data
print("Data preview:")
print(data.head())

# Convert data types - ensure all columns are numeric
for col in data.columns:
    try:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    except Exception as e:
        print(f"Warning: Could not convert column {col} to numeric: {e}")

# Fill NaN values with column means
data = data.fillna(data.mean())

print(f"Data shape after cleaning: {data.shape}")

# For simplicity, let's use the first few columns as our features
# Assuming they represent typical telematics data like speed, acceleration, etc.
feature_columns = data.columns[:10]  # First 10 columns
print(f"Using features: {feature_columns.tolist()}")

# Feature engineering for fraud detection
print("Performing feature engineering...")

# Calculate variability metrics
data['data_variability'] = data[feature_columns].std(axis=1)

# Create a synthetic fraud label based on unusual patterns
# Identifying unusual driving as high variability
threshold = np.percentile(data['data_variability'], 90)
data['fraud'] = (data['data_variability'] > threshold).astype(int)

print(f"Created dataset with {data['fraud'].sum()} fraud cases out of {len(data)} samples")

# Create a more balanced dataset
fraud_samples = data[data['fraud'] == 1]
non_fraud_samples = data[data['fraud'] == 0].sample(min(len(fraud_samples) * 3, len(data[data['fraud'] == 0])), random_state=42)
balanced_data = pd.concat([fraud_samples, non_fraud_samples])

# Select features for the model (first 10 columns plus engineered features)
fraud_features = feature_columns.tolist() + ['data_variability']

# Split features and target
X = balanced_data[fraud_features]
y = balanced_data['fraud']

# Split into training and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Standardize features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train the model
print("Training fraud detection model...")
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train_scaled, y_train)

# Evaluate model
train_accuracy = model.score(X_train_scaled, y_train)
test_accuracy = model.score(X_test_scaled, y_test)
print(f"Training accuracy: {train_accuracy:.4f}")
print(f"Test accuracy: {test_accuracy:.4f}")

# Create a dictionary with everything needed for inference
fraud_model_package = {
    'model': model,
    'scaler': scaler,
    'feature_names': fraud_features
}

# Save the model package
model_path = "models/fraud_detection.pkl"
joblib.dump(fraud_model_package, model_path)
print(f"Fraud detection model saved to {model_path}")