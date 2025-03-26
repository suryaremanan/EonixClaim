"""
Main entry point for the InsurTech application.
Handles Python path setup to avoid import errors.
"""
import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Now import and run the main app
import main

if __name__ == "__main__":
    # Run the main function from main.py
    main.main() 