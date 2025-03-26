import os
from slack_sdk import WebClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the client
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

# Upload a file
response = client.files_upload(
    channels="#insurance-claims",
    file="/home/suryaremanan/eonixclaim/test_images/car_damage.jpg",
    title="Test Car Damage",
    initial_comment="Testing file upload"
)

print(f"File uploaded: {response['file']['id']}") 