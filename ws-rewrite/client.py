import asyncio
import websockets
import json
import os
import sys

client_version = "pre-alpha V0.5.2"


saved_login_dir = os.path.join(os.getenv("APPDATA"), "ChatCLI", "saved_profiles")
os.makedirs(saved_login_dir, exist_ok=True)
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
        try:
            await websocket.send(json.dumps({"path": "connection", "client_version": client_version}))
            response = json.loads(await websocket.recv())
            print(f"Server response: {str(response)}")
        except Exception as e:
            print(e)
            sys.exit()
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
        username = input("Please enter a username: ").lower()
        password = input("Please enter a password: ")
        if username and password:
            try:
                await ws.send(json.dumps({"path" : "register", "content": "", "username": username, "receiver" : receiver, "key" : key, "password" : password}))
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
        else:
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
            saved = await check_saved_login()
            if saved:
                choice = input("Use saved login(y/n): ").lower()
                match choice:
                    case "y":
                        await ws.send(json.dumps({"path" : "login", "content": "", "username": username, "receiver" : receiver, "key" : key, "password": password}))
                        response = json.loads(await ws.recv())
                    case _:
                        continue
            else:
                password = input("Enter your password: ")
                if password:
                    await ws.send(json.dumps({"path" : "login", "content": "", "username": username, "receiver" : receiver, "key" : key, "password": password}))
                    response = json.loads(await ws.recv())
                else:
                    continue
        else:
            continue

        if response:
            if response.get("status_code") == 200:
                key = response.get("key")
                print(response.get("data"))
                if not saved:
                    match input("Save login data(y/n)?").lower():
                        case "yes":
                            await save_login()
                            break
                        case "y":
                            await save_login()
                            break
                        case _:
                            break
                break



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

async def save_login():
    with open(os.path.join(saved_login_dir, username+".txt"), "w") as f:
        f.write(password)

async def check_saved_login():
    """
    Checks if the user's login credentials are saved in the local directory.
    Returns True if valid credentials are found, otherwise False.

    Returns:
        bool: True if login is saved, False otherwise.
    """
    global username, password

    # Check if the saved login directory exists and has any files
    if os.listdir(saved_login_dir):
        try:
            with open(os.path.join(saved_login_dir, username+".txt"), "r") as f:
                password = f.read()
                if password:
                    return True
        except FileNotFoundError:
            return False
    return False

async def get_chats(ws):
    global receiver
    try:
        # Send message to the server to verify user
        await ws.send(json.dumps({"path": "get_chats", "content": "", "username": username, "receiver": receiver, "key": key}))
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Connection closed unexpectedly: {e}")
        return  # Exit or handle appropriately

    response = json.loads(await ws.recv())

    if response.get("status_code") == 200:  # Check if user is verified

        # Check if the response is valid and contains expected data
        while True:
            chats = response.get("data")
            for chat in chats:
                print(f"Chat with: {chat}")
            choice = input("Enter the name of the user you would like to talk to: ").lower()
            if choice in chats:
                receiver = choice  # Update the global receiver
                await chatting(ws)
                return
            else:
                print("Invalid selection. Try again.")

    elif response.get("status_code") == 400:
        print(response.get("error"))
        while True:
            choice = input("Who would you like to talk to, or exit(e): ").lower()
            match choice:
                case "e":
                    break
                case "exit":
                    break
                case _:
                    if choice:
                        receiver = choice
                        await ws.send(json.dumps({"path": "check_user_exist", "content": "", "username": username, "receiver": receiver, "key": key}))
                        response = json.loads(await ws.recv())
                        if response.get("status_code") == 200:
                            await chatting(ws)
                            return


    else:
        print(f"Verification failed: {response.get('error')}")

async def chatting(ws):
    #init the chats
    await ws.send(json.dumps({"path" : "chatting", "content": "", "username": username, "receiver" : receiver, "key" : key}))
    state = {"loop": True}
    async def send(websock, variable):
        while variable["loop"]:
            message = input("Your message or e to exit: ")
            if message:
                if message.lower() != "e" or message.lower() != "exit":
                    await websock.send(json.dumps({"path" : "chatting", "content": message, "username": username, "receiver" : receiver, "key" : key}))
                    asyncio.timeout(0.5)
                else:
                    variable["loop"] = False

    async def receive(websock, variable):
        log = {}
        while variable["loop"]:
            chatlog = json.loads(await websock.recv())
            for message in chatlog:
                if message not in log:
                    print(f'[{message.get("from")}: {message.get("message")}')

    await asyncio.create_task(send(ws, state))
    await asyncio.create_task(receive(ws, state))


if __name__ == "__main__":
    asyncio.run(homepage())
