import asyncio
from os.path import exists

version = "pre-alpha v1"

import websockets
import os
import json


async def receive(websock, variable):
    var = True
    log = {}
    while var:
        try:
            message_data = await websock.recv()  # Receive message data
            try:
                chatlog = json.loads(message_data)  # Parse the message data as JSON
            except json.JSONDecodeError:
                print("Received invalid JSON")
                continue  # Skip invalid data

            if not isinstance(chatlog, dict):
                print("Expected dictionary but got", type(chatlog))
                continue

            if "data" not in chatlog:
                print("Received invalid message data, no 'data' field found.")
                continue

            if chatlog.get("data") == "close":
                var = False
                websock.close()
                break

            for message in chatlog["data"]:
                message_id = f"{message.get('from')}_{message.get('datetime')}"
                if message_id not in log:
                    sender = message.get("from")
                    message_text = message.get("message")
                    print(f"[{sender}]: {message_text}")
                    log[message_id] = message

        except websockets.ConnectionClosedError as e:
            print(f"Connection closed with error: {e}")
            break
        except Exception as e:
            print(f"Unexpected error while receiving message: {e}")
            break

if __name__ == "__name__":
    os.makedirs("chat_window", exist_ok=True)
    chatcli_folder = os.path.join(os.getenv("APPDATA"), "ChatCLI", "chat_window")
    with open(os.path.join(chatcli_folder), "data.json") as f:
        data = json.load(f)
    async with websockets.connect(uri, ping_interval=10) as websocket:
        try:
            receive(websocket,)
