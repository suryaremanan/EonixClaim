import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
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

# Feature engineering for predictive maintenance
print("Performing feature engineering...")

# Calculate aggregate metrics
data['mean_value'] = data[feature_columns].mean(axis=1)
data['max_value'] = data[feature_columns].max(axis=1)
data['variability'] = data[feature_columns].std(axis=1)

# Create a synthetic maintenance score based on the data
# This would ideally be based on actual maintenance records
# Here we simulate wear and tear patterns
wear_score = (
    0.4 * data['max_value'] / data['max_value'].max() +
    0.3 * data['variability'] / data['variability'].max() +
    0.3 * data['mean_value'] / data['mean_value'].max()
)

# Calculate days until maintenance (inverse relationship with wear)
# Scale to reasonable range (7-365 days)
data['days_until_maintenance'] = ((1 - wear_score) * 358 + 7).astype(int)

print(f"Created dataset with maintenance predictions for {len(data)} samples")
print(f"Days until maintenance range: {data['days_until_maintenance'].min()} to {data['days_until_maintenance'].max()} days")

# Select features for the model
maintenance_features = feature_columns.tolist() + ['mean_value', 'max_value', 'variability']

# Split features and target
X = data[maintenance_features]
y = data['days_until_maintenance']

# Split into training and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Standardize features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train the model
print("Training predictive maintenance model...")
model = GradientBoostingRegressor(n_estimators=100, random_state=42)
model.fit(X_train_scaled, y_train)

# Evaluate model
train_rmse = np.sqrt(np.mean((model.predict(X_train_scaled) - y_train) ** 2))
test_rmse = np.sqrt(np.mean((model.predict(X_test_scaled) - y_test) ** 2))
print(f"Training RMSE: {train_rmse:.2f} days")
print(f"Test RMSE: {test_rmse:.2f} days")

# Create a dictionary with everything needed for inference
maintenance_model_package = {
    'model': model,
    'scaler': scaler,
    'feature_names': maintenance_features
}

# Save the model package
model_path = "models/predictive_maintenance.pkl"
joblib.dump(maintenance_model_package, model_path)
print(f"Predictive maintenance model saved to {model_path}") 