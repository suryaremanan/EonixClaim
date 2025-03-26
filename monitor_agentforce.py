
import os
import time
import sys

log_file = "agentforce_debug.log"

# Create log file if it doesn't exist
if not os.path.exists(log_file):
    with open(log_file, "w") as f:
        f.write("Agentforce Debug Log\n")

print(f"Monitoring {log_file} for Agentforce activity...")
print("Press Ctrl+C to stop monitoring.")

# Get the initial file size
file_size = os.path.getsize(log_file)

try:
    while True:
        # Check if file size has changed
        current_size = os.path.getsize(log_file)
        
        if current_size > file_size:
            # File has grown, read and display the new content
            with open(log_file, "r") as f:
                f.seek(file_size)
                new_content = f.read()
                sys.stdout.write(new_content)
                sys.stdout.flush()
            
            file_size = current_size
        
        time.sleep(0.5)  # Check every half second
except KeyboardInterrupt:
    print("\nStopped monitoring.")
