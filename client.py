import atexit
import json
import os
import signal
import subprocess
import sys

import requests
import re
from rich.console import Console
from rich.panel import Panel
from rich import print

# Global variables
CHATCLI_FOLDER = os.path.join(os.getenv("APPDATA"), "ChatCLI")
os.makedirs(CHATCLI_FOLDER, exist_ok=True)

LOGGED_IN = False
GLOBAL_VARS = {
    "username": "",
    "password": "",
    "email": "",
    "session_token": "",
    "receiver": "",
    "url": "https://fortbow.duckdns.org:5000/",
    "action_list": ["register", "login", "start chatting", "logout", "exit"],
    "version" : "alpha 0.2.0"
}

# Utility Functions
def is_valid_email(email):
    """Validate email format using a regex."""
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email) is not None

def verify_connection():
    global GLOBAL_VARS
    """Verify server connection."""
    print("Connecting to the server...")
    try:
        # First attempt with the existing GLOBAL_VARS["url"]
        response = requests.post(
            GLOBAL_VARS["url"] + "verify-connection",
            json={"version": GLOBAL_VARS["version"]}
        )
        if response.status_code != 200:
            print(response.json().get("error"))
        return True
    except requests.RequestException as e:
        print(f"First attempt failed: {e}")
        try:
            # Fallback to localhost
            GLOBAL_VARS["url"] = "https://localhost:5000/"
            response = requests.post(
                GLOBAL_VARS["url"] + "verify-connection",
                json={"version": "post-alpha-dev-build"}
            )
            print("[green]Connected to localhost![/]")
            return True
        except requests.RequestException as e:
            return False

def register():
    """Register a new user."""
    while True:
        username = input("Enter a username: ")
        if username.lower() in ("e", "exit"):
            return
        if any(char in username for char in r'"%\'()*+,/:;<=>?@[\]^{|}~` '):
            print("Invalid username. Try again!")
            continue
        GLOBAL_VARS["username"] = username
        break

    while True:
        password = input("Enter a password: ")
        if password.lower() in ("e", "exit"):
            return
        if any(char in password for char in r'";\ '):
            print("Invalid password. Try again!")
            continue
        import string

        if (
                len(password) < 8 or
                not any(char.isupper() for char in password) or
                not any(char.islower() for char in password) or
                not any(char.isdigit() for char in password) or
                not any(char in string.punctuation for char in password)
        ):
            print(
                "[orange]Your password must contain at least 8 characters, including an uppercase letter, a lowercase letter, a number, and a special character![/]")
            continue

        GLOBAL_VARS["password"] = password
        break

    while True:
        email = input("Enter an email: ")
        if email.lower() in ("e", "exit"):
            return
        if is_valid_email(email):
            GLOBAL_VARS["email"] = email
            break
        print("Invalid email. Try again!")

    try:
        response = requests.post(
            GLOBAL_VARS["url"] + "register",
            json={
                "username": GLOBAL_VARS["username"],
                "password": GLOBAL_VARS["password"],
                "email": GLOBAL_VARS["email"],
            },
        )
        if response.status_code != 200:
            print(response.json().get("error"))
        else:
            email_verification()
    except requests.RequestException as e:
        print(f"Error: {e}")

def email_verification():
    global LOGGED_IN
    print("A verification code has been sent to your email.")
    while True:
        email_token = input("Enter the verification code: ")
        if not email_token:
            continue
        elif email_token.lower() in ("e", "exit"):
            return
        elif not email_token.isdigit():
            print("Make sure your code only contains numbers!")
            continue
        elif not (100000 <= int(email_token) <= 999999):
            print("Invalid code format (xxxxxx)")
            continue
        else:
            try:
                response = requests.post(
                    GLOBAL_VARS["url"] + "verify-email",
                    json={
                        "username" : GLOBAL_VARS["username"],
                        "email_token" : email_token

                    }
                )
                if response.status_code != 200:
                    print(response.json().get("error"))
                else:
                    print("Account registration completed!")
                    print("Logging on...")
                    try:
                        response = requests.post(
                            GLOBAL_VARS["url"] + "login",
                            json={"username": GLOBAL_VARS["username"], "password": GLOBAL_VARS["password"]},
                        )
                        data = response.json()
                        if response.status_code == 200:
                            GLOBAL_VARS["session_token"] = data.get("session_token")
                            LOGGED_IN = True
                            print(data.get("response"))
                        else:
                            print(data.get("error"))
                    except requests.RequestException as e:
                        print(f"Error: {e}")
                    break
            except requests.RequestException as e:
                print(f"Error: {e}")

def login():
    """Log in an existing user."""
    global LOGGED_IN
    global GLOBAL_VARS

    username = input("Enter your username: ")
    if username.lower() in ("e", "exit"):
        return
    GLOBAL_VARS["username"] = username

    password = input("Enter your password ('f' if forgotten): ")
    if password.lower() in ("e", "exit"):
        return
    elif password.lower() in ("f"):
        if not username:
            GLOBAL_VARS["username"] = input("Enter your username or email: ")
        response = requests.post(
            GLOBAL_VARS["url"] + "reset-password-request", json={"data": GLOBAL_VARS["username"]}
        )
        if response.status_code != 200:
            print(response.json().get("error"))
        else:
            print(response.json().get("response"))
        return
    GLOBAL_VARS["password"] = password

    try:
        response = requests.post(
            GLOBAL_VARS["url"] + "login",
            json={"username": GLOBAL_VARS["username"], "password": GLOBAL_VARS["password"]},
        )
        data = response.json()
        if response.status_code == 200:
            GLOBAL_VARS["session_token"] = data.get("session_token")
            LOGGED_IN = True
            print(data.get("response"))
        else:
            print(data.get("error"))
    except requests.RequestException as e:
        print(f"Error: {e}")

def select_chat():
    """Select or create a chat."""
    try:
        while True:
            response = requests.post(
                GLOBAL_VARS["url"] + "fetch-chats",
                json={"username": GLOBAL_VARS["username"], "session_token": GLOBAL_VARS["session_token"]},
            )
            if response.status_code != 200:
                print(response.json().get("error"))
                return

            user_list = response.json().get("response")
            if not user_list:
                print("No chats were found.")
                while True:
                    receiver = input("Please enter the name of the person you'd like to start a conversation with: ")
                    if not receiver:
                        continue
                    if receiver.lower() in ("e", "exit"):
                            return
                    GLOBAL_VARS["receiver"] = receiver
                    response = response = requests.post(
                        GLOBAL_VARS["url"] + "create-chat",
                        json={"username": GLOBAL_VARS["username"], "session_token": GLOBAL_VARS["session_token"],
                              "receiver": GLOBAL_VARS["receiver"]},
                    )
                    if response.status_code == 200:
                        print(response.json().get("response"))
                        break
                    else:
                        print(response.json().get("error"))
                        continue
                continue

            for idx, user in enumerate(user_list, 1):
                print(f"{idx}) {user}")

            choice = input("Select a user to chat with: ")
            if not choice:
                print("Invalid choice!")
                continue
            if choice.lower() in ("e", "exit"):
                return

            if choice.isdigit() and 0 < int(choice) <= len(user_list):
                GLOBAL_VARS["receiver"] = user_list[int(choice) - 1]
            elif choice in user_list:
                GLOBAL_VARS["receiver"] = choice
            else:
                GLOBAL_VARS["receiver"] = choice
                if input("Would you like to create this chat(y/n)? ") == "y":
                    response = response = requests.post(
                        GLOBAL_VARS["url"] + "create-chat",
                        json={"username": GLOBAL_VARS["username"], "session_token": GLOBAL_VARS["session_token"], "receiver": GLOBAL_VARS["receiver"]},
                        )
                    if response.status_code == 200:
                        print(response.json().get("response"))
                    else:
                        print(response.json().get("error"))
                        continue
                else:
                    continue

            in_chat()
    except requests.RequestException as e:
        print(f"Error: {e}")

def in_chat():
    """Enter a chat session."""
    chat_data = {
        "receiver": GLOBAL_VARS["receiver"],
        "username": GLOBAL_VARS["username"],
        "session_token": GLOBAL_VARS["session_token"],
        "looping": True,
    }

    with open(os.path.join(CHATCLI_FOLDER, "data.json"), "w") as f:
        json.dump(chat_data, f, indent=4)
    
    files_dir = os.listdir()
    if "client_2.exe" in files_dir:
        subprocess.Popen('start client_2.exe', shell=True)
    elif "client_2.py" in files_dir:
        subprocess.Popen('python client_2.py', creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        print("[red]Client_2 file not found! Make sure it is located in the same folder![/]")
        return

    print("Type your message or type 'e' or 'exit' to leave.")
    while True:
        message = input()
        if message.lower() in ("exit", "e"):
            chat_data = {
                "receiver": "",
                "username": "",
                "session_token": "",
                "looping": False,
            }
            with open(os.path.join(CHATCLI_FOLDER, "data.json"), "w") as f:
                json.dump(chat_data, f, indent=4)
            break
        if message:
            try:
                response = requests.post(
                    GLOBAL_VARS["url"] + "receive-message",
                    json={
                        "username": GLOBAL_VARS["username"],
                        "receiver": GLOBAL_VARS["receiver"],
                        "session_token": GLOBAL_VARS["session_token"],
                        "message": message,
                    },
                )
                if response.status_code != 200:
                    print(response.json().get("error"))
            except requests.RequestException as e:
                print(f"Error: {e}")

def logout():
    """Log out the user."""
    global LOGGED_IN
    LOGGED_IN = False
    for key in ("username", "password", "receiver", "session_token", "email"):
        GLOBAL_VARS[key] = ""

def homepage():
    while True:
        console = Console()
        options = []
        menu_actions = []

        # Dynamically add menu options and track corresponding actions
        menu_number = 1
        if not LOGGED_IN:
            options.append(f"{menu_number}) Register")
            menu_actions.append("register")
            menu_number += 1
            options.append(f"{menu_number}) Login")
            menu_actions.append("login")
            menu_number += 1
        else:
            options.append(f"{menu_number}) Start chatting")
            menu_actions.append("start chatting")
            menu_number += 1
            options.append(f"{menu_number}) Logout")
            menu_actions.append("logout")
            menu_number += 1

        options.append(f"{menu_number}) Exit")
        menu_actions.append("exit")

        # Generate the menu string
        menu = "\n".join(options)
        header = f"Welcome to ChatCLI! [User: {GLOBAL_VARS['username']}]" if LOGGED_IN else "Welcome to ChatCLI!"

        # Use rich to display the menu
        console.print(
            Panel(menu, title=header, title_align="left", expand=False, border_style="cyan")
        )

        # Get user input and validate it
        action = input("Choose an action (ex: '1' or 'Start chatting'): ").strip().lower()
        if action.isdigit():
            action = int(action) - 1  # Convert to 0-based index
            if 0 <= action < len(menu_actions):
                action = menu_actions[action]
            else:
                print("Invalid input!")
                continue

        # Match case for the selected action
        match action:
            case "register":
                register()
            case "login":
                login()
            case "start chatting":
                select_chat()
            case "logout":
                logout()
            case "exit" | "e":
                exit()
            case _:
                print("Invalid input!")

def cleanup():
    chat_data = {
        "receiver": "",
        "username": "",
        "session_token": "",
        "looping": False,
    }

    with open(os.path.join(CHATCLI_FOLDER, "data.json"), "w") as f:
        json.dump(chat_data, f, indent=4)

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

if __name__ == "__main__":

    os.system(f"title CHATCLI {GLOBAL_VARS["version"]}")

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)  # Handles Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Handles process termination

    if verify_connection():
        try:
            homepage()
        except EOFError:
            cleanup()
    else:
        print("[red]Unable to establish a connection![/]")
