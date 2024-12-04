import asyncio
import websockets
import os
import json

version = "pre-alpha v2.1"
receiver = ""
username = ""
key = ""
server = "ws://localhost:6420"
looping = True

async def verify_connection(ws):
    try:
        await ws.send(json.dumps({"path" : "connection", "client_version" : version}))
        response = json.loads(await ws.recv())
        if response.get("status_code") == 200:
            await receive(ws)
    except Exception as e:
        print(e)

async def check_looping():
    global looping
    while looping:
        with open(os.path.join(chatcli_folder, "data.json"), "r") as file:
            file_data = json.load(file)
        looping = file_data.get("looping")
        asyncio.timeout(2)

async def receive(ws):
    await ws.send(json.dumps({"path" : "receive", "content": "", "username": username, "receiver" : receiver, "key" : key}))
    response = json.loads(await ws.recv())
    if response.get("status_code") == 400:
        print(response.get("error"))
        return
    else:
        asyncio.create_task(check_looping())
    var = True
    log = {}
    while var:
        try:
            message_data = await ws.recv()  # Receive message data
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
                ws.close()
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
    ws.close()


async def start():
    async with websockets.connect(server, ping_interval=10) as websocket:
        try:
            await verify_connection(websocket)
        except Exception as e:
            print(e)
        try:
            await receive(websocket)
        except Exception as e:
            print(e)

if __name__ == "__main__":
    os.makedirs("chat_window", exist_ok=True)
    try:
        chatcli_folder = os.path.join(os.getenv("APPDATA"), "ChatCLI", "chat_window")
        with open(os.path.join(chatcli_folder, "data.json"), "r") as f:
            data = json.load(f)
        receiver = data.get("receiver")
        username = data.get("username")
        key = data.get("key")
        server = data.get("server")
        looping = data.get("looping")
        print("Initiating Server Connection")
        asyncio.run(start())
        print("started")
    except Exception as error:
        print(error)
