from config import TelematicsConfig

def test_telematics_config():
    """Test that telematics configuration loads correctly."""
    print(f"Data path: {TelematicsConfig.DATA_PATH}")
    print(f"Risk thresholds: High={TelematicsConfig.RISK_THRESHOLD_HIGH}, Medium={TelematicsConfig.RISK_THRESHOLD_MEDIUM}")
    print(f"Driving behavior thresholds:")
    print(f"  - Acceleration: {TelematicsConfig.ACCELERATION_THRESHOLD} m/s²")
    print(f"  - Braking: {TelematicsConfig.BRAKING_THRESHOLD} m/s²")
    print(f"  - Cornering: {TelematicsConfig.CORNERING_THRESHOLD} g")
    print(f"  - Speeding: {TelematicsConfig.SPEEDING_THRESHOLD} km/h above limit")
    print(f"Driver score weights: {TelematicsConfig.DRIVER_SCORE_WEIGHTS}")
    
    # Validate configuration
    TelematicsConfig.validate()
    print("Configuration validation passed!")

if __name__ == "__main__":
    test_telematics_config() 