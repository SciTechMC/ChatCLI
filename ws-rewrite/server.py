import asyncio
import json
from textwrap import indent

import websockets
import os
import random
import string
from datetime import date, datetime
from rich import print

server_version = "pre-alpha V0.5.0"
req_client_ver = "pre-alpha V0.3.0"

async def connection(ws, client):
    print(f"Handling connection at connection")
    data = client
    try:  # Only for demo; avoid `eval` in production
        if data.get("client_version") == req_client_ver:
            await ws.send(json.dumps({"data" : "Connection successful!", "status_code" : 200}))
        else:
            await ws.send(json.dumps({"data": "Version mismatch", "status_code": 400}))
    except Exception as e:
        await ws.send(json.dumps({"data": str(e), "status_code": 400}))

async def login(ws, client):
    os.makedirs("users", exist_ok=True)
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
                        await ws.send(json.dumps({"handler" : "login" ,"data": "Login successful!", "key": str(gen_key), "status_code": 200}))
                        return
                    else:
                        await ws.send(json.dumps({"handler" : "login" ,"data": "", "status_code": 400, "error" : "Incorrect password"}))
                        return
            else:
                await ws.send(json.dumps({"handler" : "login" ,"data": "", "status_code": 400, "error" : "User not found"}))
                return
        await ws.send(json.dumps({"handler" : "login" ,"data": "", "status_code": 400,"error" : "Invalid login data"}))
    except Exception as e:
        await ws.send(json.dumps({"handler" : "login" ,"data": e, "status_code": 400}))

async def register(ws, client):
    os.makedirs("users", exist_ok=True)

    if client and "username" in client and "password" in client:
        file_path = os.path.join("users", f"{client['username']}.txt")
        if os.path.exists(file_path):
            await ws.send(json.dumps({"handler" : "register" ,"data": "", "status_code": 400, "error" : "Username already taken"}))
        with open(file_path, 'w') as f:
            f.write(client["password"])
        await ws.send(json.dumps({"handler" : "register" ,"data": "User Created successfully", "status_code": 200, "error" : ""}))
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

                    allchats_data[f"{sender}--{receiver}"] = {"Users": f"{sender},{receiver}", "date time inititated": f"{current_date} {current_time}"}

                    with open("chats.json", "w") as chats:
                        json.dump(allchats_data, chats, indent=4)

                    print(creating_file)
                    chat_data = {}

                chat_data[client_data["content"]] = \
                    {"from": sender,
                     "message" : message,
                    "datetime": f"{current_date} {current_time}",
                    "readreceipt": "unread"
                     }

                try:
                    with open(file_path, "w") as chatsfile:
                        json.dump(chat_data, chatsfile, indent=4)
                        wsoc.send(json.dumps({"handler" : "message_receive" ,"data": "Message received!", "status_code": 200, "error" : None}))
                except (FileNotFoundError, json.JSONDecodeError):
                    print("[red bold]Error with chat receive saving![/]")

            except websockets.ConnectionClosedOK:
                break
    
    async def send(wsoc, client_data):
        while True:
            try:
                await ws.send(json.dumps({"handler" : "chatting", "data" : "todo", "status_code" : 200}))
            except websockets.ConnectionClosedOK:
                break


    await asyncio.create_task(send(ws, client))
    await asyncio.create_task(receive(ws, client))

    await ws.send(json.dumps({"handler" : "chatting" ,"data": "Fetch chat not implemented yet", "status_code": 501}))
    return


async def check_user_exist(ws, client):
    data = client
    if data and data["username"]:
        if os.path.exists(f"users/{data['username']}.txt"):
            await ws.send(json.dumps({"handler" : "check_user_exist" ,"data": "Valid User", "status_code": 200, "error" : ""}))
        else:
            await ws.send(json.dumps({"handler" : "check_user_exist" ,"data": "", "status_code": 404, "error" : "Invalid User"}))
    await ws.send(json.dumps({"handler" : "check_user_exist" ,"data": "Check user exist not implemented yet", "status_code": 501}))
    return

async def handler(websocket):
    async for client in websocket:
        print(type(client))
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
            case "check-user-exist":
                await check_user_exist(websocket, client)
            case _:
                print(f"Unknown path: {path}")
                await websocket.send(json.dumps({"handler" : "main_handler" ,"data": "Unknown path", "status_code": 404}))
                await websocket.close()

async def main():
    print(f"[red]SERVER VERSION: {server_version}[/]")
    async with websockets.serve(handler, "0.0.0.0", 6420):
        print(f"WebSocket server running on 0.0.0.0:6420")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())