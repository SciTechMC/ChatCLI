import json
import os
import subprocess
import requests
import re
from rich.console import Console
from rich.panel import Panel

# Global variables
CHATCLI_FOLDER = os.path.join(os.getenv("APPDATA"), "ChatCLI")
os.makedirs(CHATCLI_FOLDER, exist_ok=True)

LOGGED_IN = False
GLOBAL_VARS = {
    "username": "",
    "password": "",
    "email": "",
    "user_key": "",
    "receiver": "",
    "url": "http://fortbow.duckdns.org:5000/",
    "action_list": ["register", "login", "start chatting", "logout", "exit"],
}

# Utility Functions
def is_valid_email(email):
    """Validate email format using a regex."""
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email) is not None


def verify_connection(url):
    """Verify server connection."""
    try:
        requests.get(url + "verify-connection")
        return True
    except requests.RequestException as e:
        print(f"Connection error: {e}")
        return False


# Features
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
        print(response.json().get("response"))
    except requests.RequestException as e:
        print(f"Error: {e}")


def login():
    """Log in an existing user."""
    global LOGGED_IN

    username = input("Enter your username: ")
    if username.lower() in ("e", "exit"):
        return
    GLOBAL_VARS["username"] = username

    password = input("Enter your password: ")
    if password.lower() in ("e", "exit"):
        return
    GLOBAL_VARS["password"] = password

    try:
        response = requests.post(
            GLOBAL_VARS["url"] + "login",
            json={"username": GLOBAL_VARS["username"], "password": GLOBAL_VARS["password"]},
        )
        data = response.json()
        if response.status_code == 200:
            GLOBAL_VARS["user_key"] = data.get("user_key")
            LOGGED_IN = True
            print(data.get("response"))
        else:
            print(data.get("error"))
    except requests.RequestException as e:
        print(f"Error: {e}")


def select_chat():
    """Select or create a chat."""
    try:
        response = requests.post(
            GLOBAL_VARS["url"] + "fetch-chats",
            json={"username": GLOBAL_VARS["username"], "user_key": GLOBAL_VARS["user_key"]},
        )
        if response.status_code != 200:
            print(response.json().get("error"))
            return

        user_list = response.json().get("response", [])
        for idx, user in enumerate(user_list, 1):
            print(f"{idx}) {user}")

        while True:
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
                        json={"username": GLOBAL_VARS["username"], "user_key": GLOBAL_VARS["user_key"], "receiver": GLOBAL_VARS["receiver"]},
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
        "user_key": GLOBAL_VARS["user_key"],
        "looping": True,
    }

    with open(os.path.join(CHATCLI_FOLDER, "data.json"), "w") as file:
        json.dump(chat_data, file, indent=4)

    subprocess.Popen('start client_2.exe', shell=True)

    print("Type your message or type 'exit' to leave.")
    while True:
        message = input()
        if message.lower() in ("exit", "e"):
            break
        if message:
            try:
                response = requests.post(
                    GLOBAL_VARS["url"] + "receive-message",
                    json={
                        "username": GLOBAL_VARS["username"],
                        "receiver": GLOBAL_VARS["receiver"],
                        "user_key": GLOBAL_VARS["user_key"],
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
    for key in ("username", "password", "receiver", "user_key", "email"):
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
        header = f"Welcome to ChatCLI! [User: {GLOBAL_VARS['username'] or 'Guest'}]"

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



if __name__ == "__main__":
    if verify_connection(GLOBAL_VARS["url"]):
        homepage()
    else:
        print("Unable to connect to the server.")
