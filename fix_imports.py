"""
Fix import issues by creating or updating __init__.py files.
"""
import os

def ensure_init_files():
    """Create __init__.py files in all directories that need them."""
    dirs_needing_init = [
        ".",
        "salesforce",
        "image_processing",
        "telematics",
        "slack",
        "slack/handlers",
        "fraud_detection",
        "blockchain",
        "ml_models",
        "utils",
        "config"
    ]
    
    for directory in dirs_needing_init:
        init_path = os.path.join(directory, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w") as f:
                f.write(f"# {directory.split('/')[-1]} package\n")
            print(f"Created {init_path}")
        else:
            print(f"{init_path} already exists")

def create_path_fix():
    """Create a path fix to add project root to Python path."""
    with open("path_fix.py", "w") as f:
        f.write("""
import os
import sys

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"Added {project_root} to Python path")
""")
    print("Created path_fix.py")

if __name__ == "__main__":
    ensure_init_files()
    create_path_fix()
    print("\nImport fixes complete. You can now run your application with:")
    print("python main.py") 