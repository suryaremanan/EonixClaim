import os
import requests
from slack_sdk import WebClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the client
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

# Path to test image
test_image = "/home/suryaremanan/eonixclaim/test_images/11.jpg"

# Upload the file
with open(test_image, "rb") as file_content:
    response = client.files_upload_v2(
        channel_id="C08HJ6LA9MM",  # Use your actual channel ID
        file=file_content,
        filename=os.path.basename(test_image),
        title="Test Car Damage",
        initial_comment="Testing file upload"
    )

print(f"File uploaded: {response['file']['id']}") 