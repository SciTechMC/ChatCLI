import asyncio
from asyncio import timeout

import websockets
import json
import os
import sys

client_version = "pre-alpha V0.4.0"

saved_login_dir = "%appdata%/ChatCLI/Saved_Profiles"
username = ""
password = ""
receiver = ""
key = ""
uri = "ws://localhost:6420/"  # Specify the route you want to connect to

async def homepage():
    """
    Displays the main menu options: Register, Log In, Exit, and Conversations (if logged in).
    Navigates to the corresponding functionality based on user input.
    """
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"path": "connection", "client_version": client_version}))
        response = await websocket.recv()
        response = json.loads(response)
        print(f"Server response: {str(response)}")
        os.makedirs(saved_login_dir, exist_ok=True)
        while True:
            print()
            print("Select action:")
            print("1. Register")
            print("2. Log In")
            print("3. Exit")
            if key:
                print("4. Conversations")
            match input(""):
                case "1":
                    await register(websocket)
                case "2":
                    await login(websocket)
                case "3":
                    sys.exit()
                case "4":
                    if key:
                        await get_chats(websocket)
                    else:
                        print("Please enter a valid number.")
                case _:
                    print("Please enter a valid number.")

async def register(ws):
    global username, password
    while True:
        username = input("Please enter a username: ")
        password = input("Please enter a password: ")
        if username and password:
            try:
                await ws.send(json.dumps({"path" : "register", "content": "", "username": username, "receiver" : receiver, "key" : key, "passowrd" : password}))
            except websockets.ConnectionClosedOK:
                print("Server unreachable!")
                break
            response = json.loads(await ws.recv())
            if response.get("status_code") == 200:
                print(response.get("data"))
                break
            elif response.get("status_code") == 400:
                print(response.get("error"))
            else:
                print("Unknown error!")

        print("Please make sure both fields are filled in!")
        choice = input("retry or exit?(r/e): ")
        match choice:
            case "r":
                continue
            case _:
                break

async def login(ws):
    global key, username, password
    while True:
        username = input("Please enter your username: ")
        if username:
            if check_saved_login():
                choice = input("Use saved login(y/n): ").lower()
                match choice:
                    case "y":
                        await ws.send(json.dumps({"path" : "login", "content": "", "username": username, "receiver" : receiver, "key" : key, "password": password}))
                        response = json.loads(await ws.recv())
                    case _:
                        continue
            password = input("Enter your password: ")
            if password:
                ws.send(json.dumps({"path" : "login", "content": "", "username": username, "receiver" : receiver, "key" : key, "password": password}))
                response = json.loads(await ws.recv())
            else:
                continue
        else:
            continue

        if response:
            if response.get("status_code") == 200:
                print(response.get("data"))
            elif response.get("status_code") == 400:
                print(response.get("error"))
                choice = input("retry or exit?(r/e): ")
                match choice:
                    case "r":
                        continue
                    case _:
                        break
        else:
            print("No response from server!")
            break

async def check_saved_login():
    """
    Checks if the user's login credentials are saved in the local directory.
    Returns True if valid credentials are found, otherwise False.

    Returns:
        bool: True if login is saved, False otherwise.
    """
    global username, password
    file_list = []

    # Check if the saved login directory exists and has any files
    if os.listdir(saved_login_dir):
        for file in os.listdir(saved_login_dir):
            file_list += [file]
            if file.endswith(".txt") and len(file_list) == 1:
                with open(os.path.join(saved_login_dir, file), "r") as f:
                    # Return True if the login details match the saved info
                    saved_username, saved_password = f.read().split(",")
                    if saved_username == username:
                        password = saved_password
                        return True
    return False

async def get_chats(ws):
    return

async def chatting(ws):
    async def send(websock):
        while True:
            message = input("")
            if message:
                await ws.send(json.dumps({"path" : "", "content": message, "username": username, "receiver" : receiver, "key" : key}))
                asyncio.timeout(0.5)

    async def receive(websock):
        log = {}
        while True:
            chatlog = json.loads(await ws.recv())
            for message in chatlog:
                if message not in log:
                    print(f'[{message.get("from")}: {message.get("message")}')

    await asyncio.create_task(send(ws))
    await asyncio.create_task(receive(ws))
#mainpage > login/register/exit/conversations


if __name__ == "__main__":
    asyncio.run(homepage())
