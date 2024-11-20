import asyncio
import json
import websockets
import os
import random
import string

server_version = "pre-alpha V0.3.0"
req_client_ver = "pre-alpha V0.3.0"

async def connection(ws, client):
    print(f"Handling connection at connection")
    data = client
    try:  # Only for demo; avoid `eval` in production
        if data.get("client_version") == req_client_ver:
            await ws.send(json.dumps({"description" : "Connection successful!", "s_code" : 200}))
        else:
            await ws.send(json.dumps({"description": "Version mismatch", "s_code": 400}))
    except Exception as e:
        await ws.send(json.dumps({"description": str(e), "s_code": 400}))

async def login(ws, client):
    os.makedirs("users", exist_ok=True)
    data = await ws.recv()
    try:
        data = eval(data)  # Only for demo; avoid `eval` in production
        if "username" in data and "password" in data:
            file_path = os.path.join("users", f"{data['username']}.txt")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    stored_password = f.read().strip()
                    if stored_password == data["password"]:
                        gen_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                        await ws.send(json.dumps({"description": "Login successful!", "key": str(gen_key), "s_code": 200}))
                        return
                    else:
                        await ws.send(json.dumps({"description": "Incorrect password", "s_code": 400}))
                        return
            else:
                await ws.send(json.dumps({"handler" : "main_handler" ,"description": "User not found", "s_code": 400}))
                return
        await ws.send(json.dumps({"handler" : "main_handler" ,"description": "Invalid login data", "s_code": 400}))
    except Exception as e:
        await ws.send(json.dumps({"handler" : "main_handler" ,"description": e, "s_code": 400}))

async def register(ws, client):
    await ws.send(json.dumps({"handler" : "main_handler" ,"description": "Register function not implemented yet", "s_code": 501}))

async def fetch_chat(ws, client):
    await ws.send(json.dumps({"handler" : "main_handler" ,"description": "Fetch chat not implemented yet", "s_code": 501}))

async def init_chat(ws, client):
    await ws.send(json.dumps({"handler" : "main_handler" ,"description": "Init chat not implemented yet", "s_code": 501}))

async def check_user_exist(ws, client):
    await ws.send(json.dumps({"handler" : "main_handler" ,"description": "Check user exist not implemented yet", "s_code": 501}))

async def send_msg(ws, client):
    await ws.send(json.dumps({"handler" : "main_handler" ,"description": "Send message not implemented yet", "s_code": 501}))

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
            case "fetch-chat":
                await fetch_chat(websocket, client)
            case "init-chat":
                await init_chat(websocket, client)
            case "check-user-exist":
                await check_user_exist(websocket, client)
            case "send-msg":
                await send_msg(websocket, client)
            case _:
                print(f"Unknown path: {path}")
                await websocket.send(json.dumps({"handler" : "main_handler" ,"description": "Unknown path", "s_code": 404}))
                await websocket.close()

async def main():
    print(f"SERVER VERSION: {server_version}")
    server = await websockets.serve(handler, "localhost", 6420)
    print(f"WebSocket server running on localhost:6420")
    #asyncio.get_event_loop().run_until_complete(start_server)
    #asyncio.get_event_loop().run_forever()
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
