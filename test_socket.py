import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the app
app = App(token=os.environ["SLACK_BOT_TOKEN"])

@app.message("hello")
def say_hello(message, say):
    say(f"Hi there! I'm working properly.")

@app.event("app_mention")
def handle_app_mention(body, say, logger):
    logger.info(body)
    say("You mentioned me!")

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    print("⚡️ Socket Mode test app is running!")
    handler.start() 