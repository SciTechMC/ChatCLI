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
            print(e)
        await asyncio.sleep(5)  # Check every 5 seconds

async def receive(ws):
    """
    Handles receiving and displaying messages from the WebSocket server.

    :param ws: WebSocket connection instance
    """
    try:
        await ws.send(json.dumps({"username": username, "receiver": receiver, "session_token": session_token}))

        while looping:
            try:
                response = json.loads(await ws.recv())

                if response.get("status_code") == 404:
                    continue
                elif response.get("status_code") != 200:
                    print(response.get("error"), response.get("status_code")
                else:
                    for message in response.get("messages"):
                        print(f"[{message.get("username")}] {message.get("message")}")
            except websockets.ConnectionClosed:
                break
    except Exception as e:
        print(e)
    finally:
        await ws.close()

async def start():
    """
    Initializes the WebSocket connection and starts message handling.
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

    if not all([receiver, username, session_token]):
        return

    try:
        async with websockets.connect(SERVER_URL) as websocket:
            # Run check_looping concurrently
            loop_task = asyncio.create_task(check_looping())
            # Handle receiving messages
            await receive(websocket)
            # Await check_looping completion (or stop it when needed)
            await loop_task
    except Exception as e:
        print(e)

def load_user_data():
    """
    Loads user data from the configuration file.

    :return: Dictionary containing user data
    """
    try:
        with open(DATA_FILE_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        return {}

if __name__ == "__main__":
    try:
        asyncio.run(start())
    except Exception as error:
        pass

    # Keep the program running for debugging purposes
    time.sleep(200)
