import asyncio
import json
import websockets
import os
import random
import string

from main import username

server_version = "pre-alpha V0.4.0"
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
    data = client
    try:
        data = eval(data)  # Only for demo; avoid `eval` in production
        if "username" in data and "password" in data:
            file_path = os.path.join("users", f"{data['username']}.txt")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    stored_password = f.read().strip()
                    if stored_password == data["password"]:
                        gen_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                        file_path = "keys.json"
                        try:
                            with open(file_path, "r") as keyfile:
                                keys = json.load(keyfile)
                        except (FileNotFoundError, json.JSONDecodeError):
                            data = {}

                        keys[data[username]] = gen_key

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
        file_path = os.path.join("users/", f"{client['username']}.txt")
        if os.path.exists(file_path):
            await ws.send(json.dumps({"handler" : "register" ,"data": "", "status_code": 400, "error" : "Username already taken"}))
        with open(file_path, 'w') as f:
            f.write(client["password"])
        await ws.send(json.dumps({"handler" : "register" ,"data": "User Created successfully", "status_code": 200, "error" : ""}))
    await ws.send(json.dumps({"handler" : "register" ,"data": "", "status_code": 400, "error" : "Invalid Signup data"}))
    return

async def chatting(ws, client):
    async def receive(ws):
        while True:
            try:
                message = await ws.recv()

            except websockets.ConnectionClosedOK:
                break

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
    print(f"SERVER VERSION: {server_version}")
    async with websockets.serve(handler, "localhost", 6420):
        await asyncio.Future()
    print(f"WebSocket server running on localhost:6420")

if __name__ == "__main__":
    asyncio.run(main())
