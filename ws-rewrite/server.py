from flask import Flask, request, jsonify
import websockets
import sys
import random

app = Flask(__name__)

async def connection(ws, path):
    server_version = "pre-alpha V0.1.0"
    await ws.recv()
    if data["client_version"] == server_version:
        return jsonify(), 200
    else:
        return jsonify(), 400

async def login(ws, path):
    os.makedirs("users", exist_ok=True)
    
    client = await websocket.recv()
    if data and "username" in data and "password" in data:
        file_path = os.path.join("users", f"{data['username']}.txt")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                stored_password = f.read().strip()
                if stored_password == data["password"]:
                    gen_key = str(
                        ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8)))
                    save_key(data["username"], gen_key)
                    return {"description": "Login successful!", "key": gen_key, "s_code" : 400}
                else:
                    return {"description": "Incorrect password", "s_code" : 400}
        else:
            return {"description": "User not found", "s_code" : 400}
    return {"description": "Invalid login data", "s_code" : 400}

async def register(ws, path):

async def fetch_chat(ws, path):

async def init_chat(ws, path):

async def check_user_exist(ws, path):

async def send_msg(ws, path):

async def main():
    server = await websockets.server(
    lambda ws, path:
        match path:
            case "/connection":
                connection(ws, path)
            case "/login":
                login(ws, path)
            case "/register":
                register(ws, path)
            case "/fetch-chat":
                fetch_chat(ws, path)
            case "/init-chat":
                init_chat(ws, path)
            case "/check-user-exist":
                check_user_exist(ws, path)
            case "/send-msg":
                send_msg(ws, path)
            case _:
                print("Wrong path!")
    )

if __name__ == "main":
    print(f"   * [red]SERVER VERSION: {server_version}[/]")
    asyncio.run(reroute)