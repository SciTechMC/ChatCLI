import asyncio
import json
import websockets
import os
import random
import string
from datetime import date, datetime
from rich import print

server_version = "pre-alpha V0.7.0"
req_client_ver = "pre-alpha V0.5.0"

os.makedirs("messages", exist_ok=True)
os.makedirs("users", exist_ok=True)

async def connection(ws, client):
    data = client
    try:  # Only for demo; avoid `eval` in production
        if data.get("client_version") == req_client_ver:
            await ws.send(json.dumps({"data" : "Connection successful!", "status_code" : 200}))
            return
        else:
            await ws.send(json.dumps({"data": "Version mismatch", "status_code": 400}))
            return
    except Exception as e:
        await ws.send(json.dumps({"data": str(e), "status_code": 400}))
        return

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

                        keys[client["username"]] = gen_key # bob : bob_key

                        with open(file_path, "w") as keyfile:
                            json.dump(keys, keyfile, indent=4)
                        await ws.send(json.dumps({"handler" : "login" ,"data": "Login successful!", "key": str(gen_key), "status_code": 200}))
                        return

                    else:
                        await ws.send(json.dumps({"handler" : "login" ,"data": "", "status_code": 400, "error" : "Incorrect password"}))
                        return

            else:
                await ws.send(json.dumps({"handler" : "login" ,"data": "", "status_code": 400, "error" : "User not found"}))
                return

        await ws.send(json.dumps({"handler" : "login" ,"data": "", "status_code": 400,"error" : "Invalid login data"}))
        return
    except Exception as e:
        await ws.send(json.dumps({"handler" : "login" ,"data": "", "status_code": 400, "error" : e}))
        return

async def register(ws, client):

    if client and client.get("username") and client.get("password"): #checks if values are not emptyu
        file_path = os.path.join("users", f"{client['username']}.txt")
        if os.path.exists(file_path): #checks if username exists
            await ws.send(json.dumps({"handler" : "register" ,"data": "", "status_code": 400, "error" : "Username already taken"}))
        with open(file_path, 'w') as f:
            f.write(client["password"])
        await ws.send(json.dumps({"handler" : "register" ,"data": "User Created successfully", "status_code": 200, "error" : ""}))
        return
    else:
        await ws.send(json.dumps({"handler" : "register" ,"data": "", "status_code": 400, "error" : "Invalid Signup data"}))
        return

async def chatting(ws, client):
    async def receive(wsoc, client_data):
        while True:
            try:
                message = await ws.recv()
                receiver = client_data["receiver"]
                sender = client_data["username"]
                current_date = date.today().strftime("%Y-%m-%d")
                current_time = datetime.now().strftime("%H:%M")
                file_path = ""
                allchats_data = {}

                if message.get("message"):
                    for file in os.listdir("messages"):
                        if receiver in file and sender in file:
                            file_path = file
                            continue

                    try:
                        with open(file_path, "r") as chatsfile:
                            chat_data = json.load(chatsfile)
                    except (FileNotFoundError, json.JSONDecodeError):
                        creating_file = open(f"{sender}--{receiver}.json", "x")
                        try:
                             with open("chats.json", "r") as allchats:
                                 allchats_data = json.load(allchats)
                        except (FileNotFoundError, json.JSONDecodeError):
                            open("chats.json", "x")

                        allchats_data[f"{sender}--{receiver}"] = {"users": f"{sender},{receiver}", "date time inititated": f"{current_date} {current_time}"}

                        with open("chats.json", "w") as chats:
                            json.dump(allchats_data, chats, indent=4)

                        print(creating_file)
                        chat_data = {}

                    chat_data[client_data["content"]] = \
                        {"from": sender,
                         "message" : message["content"],
                        "datetime": f"{current_date} {current_time}",
                        "readreceipt": "unread"
                         }

                    try:
                        with open(file_path, "w") as chatsfile:
                            json.dump(chat_data, chatsfile, indent=4)
                            await wsoc.send(json.dumps({"handler" : "message_receive" ,"data": "Message received!", "status_code": 200, "error" : None}))
                    except (FileNotFoundError, json.JSONDecodeError):
                        print("[red bold]Error with chat receive saving![/]")

            except websockets.ConnectionClosedOK:
                break

    async def send(wsoc, client_data):
        file = ""
        for file in os.listdir("messages"):
            if client_data["username"] in file and client_data["receiver"] in file:
                file = file
                continue

        while True:
            try:
                with open (os.path.join("messages", file), "r") as f:
                    chatlog = json.load(f)
                await wsoc.send(json.dumps({"handler" : "chatting", "data" : chatlog, "status_code" : 200}))
                asyncio.timeout(2)
            except websockets.ConnectionClosedOK:
                break


    await asyncio.create_task(send(ws, client))
    await asyncio.create_task(receive(ws, client))

async def check_user_exist(ws, data):
    if data and data["username"]:
        if os.path.exists(f"users/{data['username']}.txt"):
            await ws.send(json.dumps({"handler" : "check_user_exist" ,"data": "Valid User", "status_code": 200, "error" : ""}))
            return
        else:
            await ws.send(json.dumps({"handler" : "check_user_exist" ,"data": "", "status_code": 400, "error" : "Invalid User"}))
            return

async def get_chats(ws, data):
    file_path = os.path.join("messages", "chats.json")
    print("Get_chats")

    chats = []
    try:
        # Check if user is verified
        verified = await verify_user(ws, data)
        if not verified:
            return

        # Read chats from file
        with open(file_path, "r") as f:
            chats_data = json.load(f)

        if chats_data:
            for chat in chats_data:
                if data.get("username") in chat:
                    user1, user2 = chat["users"].split(",")
                    if user1 == data.get("username"):
                        chats.append(user2)
                    if user2 == data.get("username"):
                        chats.append(user1)

            if chats:
                await ws.send(json.dumps({"handler": "get_chats", "data": chats, "status_code": 200, "error": ""}))
            else:
                await ws.send(json.dumps({"handler": "get_chats", "data": [], "status_code": 400, "error": "No chats found!"}))
        else:
            empty_dict = {}
            with open(file_path, 'w') as file:
                json.dump(empty_dict, file)  # Create an empty chat file if it doesn't exist
            await ws.send(json.dumps({"handler": "get_chats", "data": [], "status_code": 400, "error": "No chats found!"}))
    except Exception as e:
        print(f"[red]Error: {str(e)}[/]")
        await ws.send(json.dumps({"handler": "get_chats", "data": "", "status_code": 500, "error": f"Failed to read chat data: {str(e)}"}))
        empty_dict = {}
        with open(file_path, 'w') as f:
            json.dump(empty_dict, f)  # Create an empty chat file if there's an error
        return

async def verify_user(ws, data):
    try:
        with open("keys.json", "r") as f:
            keys = json.load(f)
            # Validate the user and key
            if keys.get(data["username"]) != data["key"]:
                await ws.send(json.dumps({"handler": "get_chats", "data": "", "status_code": 400, "error": "Invalid username or key!"}))
                return False  # User not verified
            return True  # User verified
    except Exception as e:
        print(f"[red]{str(e)}[/]")
        await ws.send(json.dumps({"handler": "get_chats", "data": "", "status_code": 500, "error": f"Internal server error! {str(e)}"}))
        return False  # Error verifying user


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
                await websocket.send(json.dumps({"handler" : "main_handler" ,"data": "Unknown path", "status_code": 400, "error" : "Unknown path"}))
                await websocket.close()

async def main():
    print(f"[red]SERVER VERSION: {server_version}[/]")
    async with websockets.serve(handler, "0.0.0.0", 6420):
        print(f"WebSocket server running on 0.0.0.0:6420")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())