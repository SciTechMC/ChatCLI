import asyncio
import time
import websockets
import os
import json

# Constants
CHATCLI_FOLDER = os.path.join(os.getenv("APPDATA"), "ChatCLI")
DATA_FILE_PATH = os.path.join(CHATCLI_FOLDER, "data.json")
SERVER_URL = "wss://fortbow.duckdns.org:8765"

# Global variables for user and connection details
receiver = ""
username = ""
session_token = ""
looping = True


async def check_looping():
    """
    Periodically checks the 'looping' flag from the data file and updates the global variable.
    """
    global looping
    while looping:
        try:
            with open(DATA_FILE_PATH, "r") as file:
                looping = json.load(file).get("looping")
                if not looping:
                    exit()
        except Exception as e:
            print(f"Error checking looping flag: {e}")
        await asyncio.sleep(5)  # Check every 5 seconds


async def receive(ws):
    """
    Handles receiving and displaying messages from the WebSocket server.

    :param ws: WebSocket connection instance
    """
    global looping

    # Send initial authentication request
    await ws.send(json.dumps({"username": username, "receiver": receiver, "session_token": session_token}))

    try:
        # Start a background task to monitor the looping flag
        asyncio.create_task(check_looping())

        while looping:
            with open(DATA_FILE_PATH, 'r') as f:
                data = json.load(f)
                if not data.get("looping"):
                    exit()

    except Exception as e:
        print(f"Error receiving messages: {e}")
    finally:
        await ws.close()


async def start():
    """
    Initializes the WebSocket connection and starts message handling.
    """
    try:
        async with websockets.connect(SERVER_URL) as websocket:
            await receive(websocket)
    except Exception as e:
        print(f"Connection error: {e}")


def load_user_data():
    """
    Loads user data from the configuration file.

    :return: Dictionary containing user data
    """
    try:
        with open(DATA_FILE_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading user data: {e}")
        return {}


def initialize():
    """
    Initializes the application, loading user data and preparing for connection.
    """
    global receiver, username, session_token, looping

    # Ensure the chat data directory exists
    os.makedirs(CHATCLI_FOLDER, exist_ok=True)

    # Load user data
    file_data = load_user_data()
    receiver = file_data.get("receiver", "")
    username = file_data.get("username", "")
    session_token = file_data.get("session_token", "")
    looping = file_data.get("looping", True)


if __name__ == "__main__":
    initialize()
    try:
        asyncio.run(start())
    except Exception as error:
        print(f"Initialization error: {error}")

    # Keep the program running for debugging purposes
    time.sleep(200)
