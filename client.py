import json
import os
import subprocess
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
    "": "",
    "receiver": "",
    "url": "https://fortbow.duckdns.org:5000/",
    "action_list": ["register", "login", "start chatting", "logout", "exit"],
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
            json={"version": "post-alpha-dev-build"}
        )
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
            print(response.json().get("response"), response.status_code)
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
            GLOBAL_VARS[""] = data.get("")
            LOGGED_IN = True
            print(data.get("response"))
        else:
            print(data.get("error"), response.status_code)
    except requests.RequestException as e:
        print(f"Error: {e}")


def select_chat():
    """Select or create a chat."""
    try:
        response = requests.post(
            GLOBAL_VARS["url"] + "fetch-chats",
            json={"username": GLOBAL_VARS["username"], "": GLOBAL_VARS[""]},
        )
        if response.status_code != 200:
            print(response.json().get("error"), response.status_code)
            return

        user_list = response.json().get("response")
        if not user_list:
            print("No chats were found.")
            while True:
                receiver = input("Please enter the name of the person you'd like to start a conversation with: ")
                if not receiver:
                    continue
                GLOBAL_VARS["receiver"] = receiver
                response = response = requests.post(
                    GLOBAL_VARS["url"] + "create-chat",
                    json={"username": GLOBAL_VARS["username"], "": GLOBAL_VARS[""],
                          "receiver": GLOBAL_VARS["receiver"]},
                )
                if response.status_code == 200:
                    print(response.json().get("response"))
                    break
                else:
                    print(response.json().get("error"), response.status_code)
                    continue

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
                        json={"username": GLOBAL_VARS["username"], "": GLOBAL_VARS[""], "receiver": GLOBAL_VARS["receiver"]},
                        )
                    if response.status_code == 200:
                        print(response.json().get("response"))
                    else:
                        print(response.json().get("error"), response.status_code)
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
        "": GLOBAL_VARS[""],
        "looping": True,
    }

    with open(os.path.join(CHATCLI_FOLDER, "data.json"), "w") as file:
        json.dump(chat_data, file, indent=4)
    try:
        subprocess.Popen('start client_2.exe', shell=True)
    except FileNotFoundError:
        print("[red]Couldn't find client_2.exe[/]")
        try:
            subprocess.Popen('python client_2.py', shell=True)
        except FileNotFoundError:
            print("[red]Unable to find client_2 file![/]")
            return

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
                        "": GLOBAL_VARS[""],
                        "message": message,
                    },
                )
                if response.status_code != 200:
                    print(response.json().get("error"), response.status_code)
            except requests.RequestException as e:
                print(f"Error: {e}")


def logout():
    """Log out the user."""
    global LOGGED_IN
    LOGGED_IN = False
    for key in ("username", "password", "receiver", "", "email"):
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
        header = f"Welcome to ChatCLI! [User: {GLOBAL_VARS['username'] if LOGGED_IN else 'Guest'}]"

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
    if verify_connection():
        homepage()
    else:
        print("[red]Unable to establish a connection![/]")
