import os
from dotenv import load_dotenv

load_dotenv()

class TelematicsConfig:
    """Configuration for telematics data processing."""
    
    # Base paths
    DATA_PATH = os.getenv("TELEMATICS_DATA_PATH", "data/telematics")
    
    # Risk thresholds
    RISK_THRESHOLD_HIGH = float(os.getenv("RISK_THRESHOLD_HIGH", 0.75))
    RISK_THRESHOLD_MEDIUM = float(os.getenv("RISK_THRESHOLD_MEDIUM", 0.5))
    
    # Processing parameters
    SAMPLING_RATE = float(os.getenv("TELEMATICS_SAMPLING_RATE", 1))
    
    # Driving behavior thresholds
    ACCELERATION_THRESHOLD = float(os.getenv("ACCELERATION_THRESHOLD", 0.2))
    BRAKING_THRESHOLD = float(os.getenv("BRAKING_THRESHOLD", -0.3))
    CORNERING_THRESHOLD = float(os.getenv("CORNERING_THRESHOLD", 0.25))
    SPEEDING_THRESHOLD = float(os.getenv("SPEEDING_THRESHOLD", 10))
    
    # Scoring weights
    DRIVER_SCORE_WEIGHTS = {
        "acceleration": float(os.getenv("DRIVER_SCORE_WEIGHT_ACCEL", 0.25)),
        "braking": float(os.getenv("DRIVER_SCORE_WEIGHT_BRAKING", 0.25)),
        "speeding": float(os.getenv("DRIVER_SCORE_WEIGHT_SPEED", 0.3)),
        "cornering": float(os.getenv("DRIVER_SCORE_WEIGHT_CORNER", 0.2))
    }
    
    # Anomaly detection
    ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_DETECTION_THRESHOLD", 3.0))
    
    @classmethod
    def validate(cls):
        """Validate configuration values."""
        assert os.path.exists(cls.DATA_PATH), f"Telematics data path {cls.DATA_PATH} does not exist"
        assert 0 <= cls.RISK_THRESHOLD_MEDIUM <= cls.RISK_THRESHOLD_HIGH <= 1, "Risk thresholds must be in ascending order between 0 and 1"
        assert sum(cls.DRIVER_SCORE_WEIGHTS.values()) == 1.0, "Driver score weights must sum to 1.0" 