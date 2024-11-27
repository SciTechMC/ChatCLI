import asyncio
import json
import websockets
import os
import random
import string
from datetime import date, datetime
from rich import print

#import logging
#logger = logging.getLogger('websockets')
#logger.setLevel(logging.DEBUG)
#logger.addHandler(logging.StreamHandler())

server_version = "pre-alpha V0.8.3"
req_client_ver = "pre-alpha V0.6.2"

os.makedirs("messages", exist_ok=True)
os.makedirs("users", exist_ok=True)


# Helper function to log user actions
def log_action(action, username=None, additional_info=""):
    if username:
        print(f"[blue]Action: {action}[/] [green]User: {username}[/] {additional_info}")
    else:
        print(f"[blue]Action: {action}[/] {additional_info}")


async def connection(ws, client):
    data = client
    try:
        ip = ws.remote_address[0]  # Get client's IP address
        log_action("Client connected", None, f"IP: {ip}")

        if data.get("client_version") == req_client_ver:
            await ws.send(json.dumps({"data": "Connection successful!", "status_code": 200}))
            log_action("Connection successful", data.get("username"))
        else:
            await ws.send(json.dumps({"data": "Version mismatch", "status_code": 400}))
            log_action("Connection failed", None, "Version mismatch")
    except Exception as e:
        await ws.send(json.dumps({"data": str(e), "status_code": 400}))
        log_action("Connection error", None, f"Error: {e}")


async def login(ws, client):
    try:
        if "username" in client and "password" in client:
            file_path = os.path.join("users", f"{client['username']}.txt")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    stored_password = f.read().strip()
                    if stored_password == client["password"]:
                        gen_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                        file_path = "keys.json"
                        try:
                            with open(file_path, "r") as keyfile:
                                keys = json.load(keyfile)
                        except (FileNotFoundError, json.JSONDecodeError):
                            keys = {}

                        keys[client["username"]] = gen_key
                        with open(file_path, "w") as keyfile:
                            json.dump(keys, keyfile, indent=4)

                        await ws.send(json.dumps(
                            {"handler": "login", "data": "Login successful!", "key": str(gen_key), "status_code": 200}))
                        log_action("User logged in", client["username"])
                        return
                    else:
                        await ws.send(json.dumps(
                            {"handler": "login", "data": "", "status_code": 400, "error": "Incorrect password"}))
                        log_action("Login failed", client["username"], "Incorrect password")
                        return

            else:
                await ws.send(
                    json.dumps({"handler": "login", "data": "", "status_code": 400, "error": "User not found"}))
                log_action("Login failed", client["username"], "User not found")
                return

        await ws.send(json.dumps({"handler": "login", "data": "", "status_code": 400, "error": "Invalid login data"}))
        log_action("Login failed", None, "Invalid login data")
    except Exception as e:
        await ws.send(json.dumps({"handler": "login", "data": "", "status_code": 400, "error": str(e)}))
        log_action("Login error", None, f"Error: {e}")


async def register(ws, client):
    if client and client.get("username") and client.get("password"):
        file_path = os.path.join("users", f"{client['username']}.txt")
        if os.path.exists(file_path):
            await ws.send(
                json.dumps({"handler": "register", "data": "", "status_code": 400, "error": "Username already taken"}))
            log_action("Registration failed", client["username"], "Username already taken")
        else:
            with open(file_path, 'w') as f:
                f.write(client["password"])
            await ws.send(json.dumps(
                {"handler": "register", "data": "User Created successfully", "status_code": 200, "error": ""}))
            log_action("User registered", client["username"])
    else:
        await ws.send(
            json.dumps({"handler": "register", "data": "", "status_code": 400, "error": "Invalid Signup data"}))
        log_action("Registration failed", None, "Invalid Signup data")


async def chatting(ws, client_data):
    # Inner function to handle receiving messages from the WebSocket
    async def receive(webs, data):
        while True:  # Continuously listen for incoming messages
            try:
                # Receive a message from the WebSocket and parse it as JSON
                message = await webs.recv()
                message = json.loads(message)

                # Extract sender, receiver, and current timestamp
                receiver = data["receiver"]
                sender = data["username"]
                current_date = date.today().strftime("%Y-%m-%d")
                current_time = datetime.now().strftime("%H:%M")

                file_path = ""  # Initialize file path for storing chat messages
                chat_data = {}  # Initialize an empty dictionary for chat data

                # Check if the received message contains content
                if message.get("content"):
                    # Search for an existing chat file between the sender and receiver
                    for file in os.listdir("messages"):
                        if receiver in file and sender in file:
                            file_path = os.path.join("messages", file)
                            break

                    if not file_path:  # Log if no matching chat file is found
                        log_action("Chat file not found", sender, f"Receiver: {receiver}")

                        try:
                            # Attempt to open the chat file and load existing data
                            file_p = os.path.join("messages", "chats.json")
                            with open(file_p, "r") as chatsfile:
                                chats_data = json.load(chatsfile)

                            chats_data[f"{sender}--{receiver}"] = {
                                "users": f"{sender},{receiver}",
                                "datetime_init": f"{current_date} {current_time}"
                            }
                            with open(file_p, "r") as chatsfile:
                                json.dump(chats_data, chatsfile, indent=4)
                            open(os.path.join("messages", f"{sender}--{receiver}"), "w")
                        except FileNotFoundError:
                            # Handle the case where the chat file doesn't exist
                            print(f"File not found: {file_path}, creating a new one.")
                            open(f"messages/{sender}--{receiver}.json", "w")
                            file_path = f"messages/{sender}--{receiver}.json"
                            chat_data = {}

                    # Append the new message to the chat data
                    chat_data = chat_data.get("messages", [])
                    chat_data.append({
                        "from": sender,
                        "message": message["content"],
                        "datetime": f"{current_date} {current_time}",
                        "readreceipt": "unread"
                    })

                    try:
                        # Save the updated chat data back to the chat file
                        with open(file_path, "w") as chatsfile:
                            json.dump({"messages": chat_data}, chatsfile, indent=4)
                        log_action("Message sent", sender, f"Receiver: {receiver} | Message: {message['content']}")
                    except Exception as e:
                        # Log any errors encountered while saving the message
                        print(f"Error saving message to chat file: {e}")

            except websockets.ConnectionClosedOK:  # Handle WebSocket disconnection
                break
            except Exception as e:  # Handle unexpected errors
                print(f"Unexpected error: {e}")
                break

    # Inner function to handle sending chat data to the WebSocket
    async def send(webs, data):
        file_path = ""  # Initialize file path for storing chat messages

        # Search for the chat file corresponding to the sender and receiver
        for file in os.listdir("messages"):
            if data["username"] in file and data["receiver"] in file:
                file_path = os.path.join("messages", file)
                break

        if not file_path:  # If no file is found, create a new one
            print("Chat file not found, creating.")
            file_path = os.path.join("messages", f'{data["username"]}--{data["receiver"]}.json')
            try:
                with open(file_path, 'w') as f:
                    empty_dict = {}
                    json.dump(empty_dict, f, indent=4)  # Initialize with an empty JSON object
            except Exception as e:
                print(str(e))  # Log any errors while creating the file

        while True:  # Continuously send chat data to the WebSocket
            try:
                if not os.path.exists(file_path):  # Verify the file exists
                    print(f"Chat file '{file_path}' not found.")
                    break

                # Load chat data from the file
                with open(file_path, "r") as f:
                    chat_data = json.load(f)

                # Extract the list of messages from the chat data
                chat_data_list = chat_data.get("messages", [])

                # Send the chat data to the WebSocket
                await webs.send(json.dumps({"handler": "chatting", "data": chat_data_list, "status_code": 200}))

                log_action("Chat data sent", data["username"], f"Receiver: {data['receiver']}")

                # Pause for 2 seconds before sending the next update
                await asyncio.sleep(2)

            except websockets.ConnectionClosedOK:  # Handle WebSocket disconnection
                break
            except Exception as e:  # Handle unexpected errors
                print(f"Error while sending chatlog: {e}")
                break

    # Run both receive and send functions concurrently
    await asyncio.gather(receive(ws, client_data), send(ws, client_data))


async def check_user_exist(ws, data):
    if data and data["username"]:
        if os.path.exists(f"users/{data['username']}.txt"):
            await ws.send(
                json.dumps({"handler": "check_user_exist", "data": "Valid User", "status_code": 200, "error": ""}))
            log_action("User check", data["username"], "Valid User")
        else:
            await ws.send(
                json.dumps({"handler": "check_user_exist", "data": "", "status_code": 400, "error": "Invalid User"}))
            log_action("User check", data["username"], "Invalid User")

async def get_chats(ws, data):
    # Define the path to the chats.json file
    file_path = os.path.join("messages", "chats.json")
    chats = []  # Initialize an empty list to store the chat partners

    try:
        # Check if chats.json exists; if not, create it and initialize with an empty dictionary
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump({}, f)  # Create an empty JSON object
            print("Created new chats.json file.")

        # Verify the user's credentials using the verify_user function
        verified = await verify_user(ws, data)
        if not verified:  # If verification fails, stop execution
            return

        # Open and load the chats.json file
        with open(file_path, "r") as f:
            chats_data = json.load(f)  # Parse the JSON content into a Python dictionary

        print(f"chats_data: {chats_data}")  # Debugging: Log the chat data

        # Ensure chats_data is a dictionary before processing
        if isinstance(chats_data, dict):
            # Iterate through all chat records in the file
            for chat_key, chat in chats_data.items():
                if "users" in chat:  # Ensure the "users" key exists in the chat
                    user1, user2 = chat["users"].split(",")  # Split the users
                    # Add the other participant to the chats list if the username matches
                    if user1 == data.get("username"):
                        chats.append(user2)
                    elif user2 == data.get("username"):
                        chats.append(user1)

            # If chats are found, send them to the client
            if chats:
                await ws.send(json.dumps({
                    "handler": "get_chats",
                    "data": chats,
                    "status_code": 200,
                    "error": ""
                }))
                log_action("Chats fetched", data["username"], f"Chats: {chats}")  # Log the action
            else:
                # If no chats are found, inform the client with an error message
                await ws.send(json.dumps({
                    "handler": "get_chats",
                    "data": [],
                    "status_code": 400,
                    "error": "No chats found!"
                }))
                log_action("No chats found", data["username"])  # Log the absence of chats

    except Exception as e:
        # Handle any exceptions that occur during processing
        print(f"[red]Error: {str(e)}[/]")  # Debugging: Print the error in red
        # Inform the client about the failure and send the error message
        await ws.send(json.dumps({
            "handler": "get_chats",
            "data": "",
            "status_code": 500,
            "error": f"Failed to read chat data: {str(e)}"
        }))
        # Reset the chats.json file to an empty dictionary to recover from corruption
        with open(file_path, 'w') as f:
            json.dump({}, f)  # Overwrite with an empty JSON object
        return

async def verify_user(ws, data):
    try:
        with open("keys.json", "r") as f:
            keys = json.load(f)
            if keys.get(data["username"]) != data["key"]:
                await ws.send(json.dumps(
                    {"handler": "get_chats", "data": "", "status_code": 400, "error": "Invalid username or key!"}))
                return False
            return True
    except Exception as e:
        print(f"[red]{str(e)}[/]")
        await ws.send(json.dumps(
            {"handler": "get_chats", "data": "", "status_code": 500, "error": f"Internal server error! {str(e)}"}))
        return False

async def handler(websocket):
    async for client in websocket:
        client = json.loads(client)
        path = client.get("path")
        match path:
            case "connection":
                await connection(websocket, client)
            case "login":
                await login(websocket, client)
            case "register":
                await register(websocket, client)
            case "chatting":
                await chatting(websocket, client)
            case "check_user_exist":
                await check_user_exist(websocket, client)
            case "get_chats":
                await get_chats(websocket, client)
            case "verify_user":
                await verify_user(websocket, client)
            case _:
                print(f"Unknown path: {path}")
                await websocket.send(json.dumps(
                    {"handler": "main_handler", "data": "Unknown path", "status_code": 400, "error": "Unknown path"}))
                await websocket.close()

async def main():
    print(f"[red]SERVER VERSION: {server_version}[/]")
    async with websockets.serve(handler, "0.0.0.0", 6420):
        print(f"WebSocket server running on 0.0.0.0:6420")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
