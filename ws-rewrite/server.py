import asyncio
import websockets
import os
import random
import string

server_version = "pre-alpha V0.1.0"

async def connection(ws, path):
    print(f"Handling connection at {path}")
    data = await ws.recv()
    try:
        data = eval(data)  # Only for demo; avoid `eval` in production
        if data.get("client_version") == server_version:
            await ws.send('{"description": "Connection successful!", "s_code": 200}')
        else:
            await ws.send('{"description": "Version mismatch", "s_code": 400}')
    except Exception as e:
        await ws.send(f'{{"description": "Error: {str(e)}", "s_code": 400}}')

async def login(ws, path):
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
                        await ws.send(f'{{"description": "Login successful!", "key": "{gen_key}", "s_code": 200}}')
                        return
                    else:
                        await ws.send('{"description": "Incorrect password", "s_code": 400}')
                        return
            else:
                await ws.send('{"description": "User not found", "s_code": 400}')
                return
        await ws.send('{"description": "Invalid login data", "s_code": 400}')
    except Exception as e:
        await ws.send(f'{{"description": "Error: {str(e)}", "s_code": 400}}')

async def register(ws, path):
    await ws.send('{"description": "Register function not implemented yet", "s_code": 501}')

async def fetch_chat(ws, path):
    await ws.send('{"description": "Fetch chat not implemented yet", "s_code": 501}')

async def init_chat(ws, path):
    await ws.send('{"description": "Init chat not implemented yet", "s_code": 501}')

async def check_user_exist(ws, path):
    await ws.send('{"description": "Check user exist not implemented yet", "s_code": 501}')

async def send_msg(ws, path):
    await ws.send('{"description": "Send message not implemented yet", "s_code": 501}')

async def handler(ws):
    print(str(ws))
    path : str = "0"
    match path:
        case "/connection":
            await connection(ws, path)
        case "/login":
            await login(ws, path)
        case "/register":
            await register(ws, path)
        case "/fetch-chat":
            await fetch_chat(ws, path)
        case "/init-chat":
            await init_chat(ws, path)
        case "/check-user-exist":
            await check_user_exist(ws, path)
        case "/send-msg":
            await send_msg(ws, path)
        case _:
            print(f"Unknown path: {path}")
            await ws.send('{"description": "Unknown path", "s_code": 404}')

async def main():
    print(f"SERVER VERSION: {server_version}")
    server = await websockets.serve(handler, "localhost", 6420)
    print("WebSocket server running on ws://0.0.0.0:6420")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
