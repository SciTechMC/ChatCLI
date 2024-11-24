import asyncio
import json
import websockets
import os
import random
import string
from datetime import date, datetime
from rich import print
import logging

logger = logging.getLogger('websockets')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

server_version = "pre-alpha V0.8.7"
req_client_ver = "pre-alpha V0.6.1"

os.makedirs("messages", exist_ok=True)
os.makedirs("users", exist_ok=True)


# Helper function to log user actions
def log_action(action, username=None, additional_info=""):
    return
    #if username:
    #    print(f"[blue]Action: {action}[/] [green]User: {username}[/] {additional_info}")
    #else:
    #    print(f"[blue]Action: {action}[/] {additional_info}")


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
    async def receive(webs, data):
        while True:
            try:
                message = await webs.recv()
                message = json.loads(message)
                receiver = data["receiver"]
                sender = data["username"]
                current_date = date.today().strftime("%Y-%m-%d")
                current_time = datetime.now().strftime("%H:%M")
                file_path = ""
                chat_data = {}

                if message.get("content"):
                    for file in os.listdir("messages"):
                        if receiver in file and sender in file:
                            file_path = os.path.join("messages", file)
                            break

                    if not file_path:
                        log_action("Chat file not found", sender, f"Receiver: {receiver}")

                    try:
                        with open(file_path, "r") as chatsfile:
                            chat_data = json.load(chatsfile)
                    except FileNotFoundError:
                        print(f"File not found: {file_path}, creating a new one.")
                        creating_file = open(f"messages/{sender}--{receiver}.json", "x")
                        file_path = f"messages/{sender}--{receiver}.json"
                        chat_data = {}

                    chat_data = chat_data.get("messages", [])
                    chat_data.append({
                        "from": sender,
                        "message": message["content"],
                        "datetime": f"{current_date} {current_time}",
                        "readreceipt": "unread"
                    })

                    try:
                        with open(file_path, "w") as chatsfile:
                            json.dump({"messages": chat_data}, chatsfile, indent=4)
                            await webs.send(json.dumps(
                                {"handler": "message_receive", "data": "Message received!", "status_code": 200,
                                 "error": None}))
                        log_action("Message sent", sender, f"Receiver: {receiver} | Message: {message['content']}")
                    except Exception as e:
                        print(f"Error saving message to chat file: {e}")

            except websockets.ConnectionClosedOK:
                break
            except Exception as e:
                print(f"Unexpected error: {e}")
                break

    async def send(webs, data):
        file_path = ""

        for file in os.listdir("messages"):
            if data["username"] in file and data["receiver"] in file:
                file_path = os.path.join("messages", file)
                break

        if not file_path:
            print("Chat file not found, creating.")
            file_path = os.path.join("messages", f'{data["username"]}--{data["receiver"]}.json')
            open(file_path, 'x')

        while True:
            try:
                if not os.path.exists(file_path):
                    print(f"Chat file '{file_path}' not found.")
                    break

                with open(file_path, "r") as f:
                    chat_data = json.load(f)

                chat_data_list = chat_data.get("messages", [])

                await webs.send(json.dumps({"handler": "chatting", "data": chat_data_list, "status_code": 200}))

                log_action("Chat data sent", data["username"], f"Receiver: {data['receiver']}")
                await asyncio.sleep(2)

            except websockets.ConnectionClosedOK:
                break
            except Exception as e:
                print(f"Error while sending chatlog: {e}")
                break

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
    file_path = os.path.join("messages", "chats.json")
    chats = []
    try:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump({}, f)
            print("Created new chats.json file.")

        verified = await verify_user(ws, data)
        if not verified:
            return

        with open(file_path, "r") as f:
            chats_data = json.load(f)

        print(f"chats_data: {chats_data}")

        if isinstance(chats_data, dict):
            for chat_key, chat in chats_data.items():
                if "users" in chat:
                    user1, user2 = chat["users"].split(",")
                    if user1 == data.get("username"):
                        chats.append(user2)
                    elif user2 == data.get("username"):
                        chats.append(user1)

            if chats:
                await ws.send(json.dumps({"handler": "get_chats", "data": chats, "status_code": 200, "error": ""}))
                log_action("Chats fetched", data["username"], f"Chats: {chats}")
            else:
                await ws.send(
                    json.dumps({"handler": "get_chats", "data": [], "status_code": 400, "error": "No chats found!"}))
                log_action("No chats found", data["username"])

    except Exception as e:
        print(f"[red]Error: {str(e)}[/]")
        await ws.send(json.dumps(
            {"handler": "get_chats", "data": "", "status_code": 500, "error": f"Failed to read chat data: {str(e)}"}))
        with open(file_path, 'w') as f:
            json.dump({}, f)
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
