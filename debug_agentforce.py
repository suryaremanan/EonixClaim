"""
Debug utility for monitoring Agentforce and Einstein GPT simulation.
"""
import os
import re
import logging

# Configure more detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='agentforce_debug.log',  # Output to file
    filemode='a'  # Append mode
)

logger = logging.getLogger("agentforce_debug")

# Update Agentforce manager to add detailed logging
agentforce_path = "salesforce/agentforce.py"
with open(agentforce_path, "r") as f:
    content = f.read()

# Add debug logging to trigger_claim_processing_agent method
enhanced_content = content.replace(
    "def trigger_claim_processing_agent(self, claim_id, damage_report, channel_id=None, client=None):",
    """def trigger_claim_processing_agent(self, claim_id, damage_report, channel_id=None, client=None):
        # Debug logging
        import logging
        logger = logging.getLogger("agentforce_debug")
        logger.debug(f"\\n{'='*50}\\nTRIGGERING CLAIM PROCESSING AGENT\\n{'='*50}")
        logger.debug(f"Claim ID: {claim_id}")
        logger.debug(f"Damage Report: {damage_report}")
        logger.debug(f"Channel ID: {channel_id}")"""
)

# Add debug logging to the _simulate_einstein_gpt_response method
enhanced_content = enhanced_content.replace(
    "def _simulate_einstein_gpt_response(self, damage_report):",
    """def _simulate_einstein_gpt_response(self, damage_report):
        # Debug logging
        import logging
        logger = logging.getLogger("agentforce_debug")
        logger.debug(f"\\n{'='*50}\\nSIMULATING EINSTEIN GPT RESPONSE\\n{'='*50}")
        logger.debug(f"Damage Report Input: {damage_report}")"""
)

# Add logging for the response blocks being generated
enhanced_content = enhanced_content.replace(
    "return blocks",
    """logger.debug(f"Generated blocks: {blocks}")
        return blocks"""
)

with open(agentforce_path, "w") as f:
    f.write(enhanced_content)

print("Added enhanced debugging to Agentforce manager")

# Create a quick inspector script to monitor logs in real-time
monitor_script = "monitor_agentforce.py"
with open(monitor_script, "w") as f:
    f.write("""
import os
import time
import sys

log_file = "agentforce_debug.log"

# Create log file if it doesn't exist
if not os.path.exists(log_file):
    with open(log_file, "w") as f:
        f.write("Agentforce Debug Log\\n")

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
    print("\\nStopped monitoring.")
""")

print(f"Created monitor script at {monitor_script}")
print("\nTo monitor Agentforce activity in real-time:")
print("1. Open a new terminal window")
print("2. Run: python monitor_agentforce.py")
print("3. Upload an image to Slack in your main application")
print("4. Watch the debug output in the monitor window") 