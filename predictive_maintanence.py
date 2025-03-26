import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import os

# Create directory for models if it doesn't exist
os.makedirs("models", exist_ok=True)

def generate_maintenance_training_data(n_samples=10000):
    """Generate synthetic vehicle telematics data for training predictive maintenance model."""
    np.random.seed(42)
    
    # Generate features
    data = {
        'vehicle_age': np.random.randint(0, 15, n_samples),  # Vehicle age in years
        'total_mileage': np.random.randint(0, 200000, n_samples),  # Total vehicle mileage
        'avg_engine_load': np.random.uniform(20, 80, n_samples),  # Average engine load (%)
        'avg_engine_rpm': np.random.normal(2000, 500, n_samples),  # Average engine RPM
        'high_rpm_pct': np.random.uniform(0, 30, n_samples),  # % time spent at high RPM
        'harsh_accel_count': np.random.poisson(5, n_samples),  # Number of harsh accelerations
        'harsh_brake_count': np.random.poisson(3, n_samples),  # Number of harsh brakings
        'ambient_temp_avg': np.random.normal(20, 10, n_samples),  # Average ambient temperature (C)
        'battery_voltage': np.random.normal(12.5, 0.5, n_samples),  # Battery voltage
        'coolant_temp_high_pct': np.random.uniform(0, 15, n_samples),  # % time with high coolant temp
        'error_code_count': np.random.poisson(0.5, n_samples)  # Number of error codes
    }
    
    # Calculate days until maintenance needed based on vehicle characteristics
    days_until_maintenance = (
        365 - data['vehicle_age'] * 20 -  # Older vehicles need maintenance sooner
        data['total_mileage'] * 0.001 -  # Higher mileage means sooner maintenance
        data['high_rpm_pct'] * 2 -  # High RPM usage accelerates wear
        data['harsh_accel_count'] * 5 -  # Harsh acceleration accelerates wear
        data['harsh_brake_count'] * 3 -  # Harsh braking accelerates wear
        data['error_code_count'] * 30 +  # Error codes indicate problems
        (data['battery_voltage'] - 12) * 40  # Lower battery voltage may indicate issues
    )
    
    # Add noise and ensure values are reasonable (between 0 and 365 days)
    days_until_maintenance = days_until_maintenance + np.random.normal(0, 30, n_samples)
    days_until_maintenance = np.clip(days_until_maintenance, 0, 365)
    
    # Create DataFrame
    df = pd.DataFrame(data)
    df['days_until_maintenance'] = days_until_maintenance.astype(int)
    
    return df

# Generate and prepare data
data = generate_maintenance_training_data()
print(f"Generated {len(data)} training examples for predictive maintenance")

# Split features and target
X = data.drop('days_until_maintenance', axis=1)
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
    'feature_names': list(X.columns)
}

# Save the model package
model_path = "models/predictive_maintenance.pkl"
joblib.dump(maintenance_model_package, model_path)
print(f"Predictive maintenance model saved to {model_path}")