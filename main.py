import sys
import requests
from datetime import date
import os

from flask import jsonify
from rich import print
import multiprocessing
import time

# Global Variables
server_config = {}
username = ""
password = ""
receiver = ""
key = ""
saved_login_dir = os.getenv("USERPROFILE") + "/Documents/PythonChatApp/Saved-Profiles/"
current_date = date.today().strftime("%Y-%m-%d")


# --------------------------------------------------------------------------------
# Homepage Navigation
# --------------------------------------------------------------------------------

def homepage():
    """
    Displays the main menu options: Register, Log In, Exit, and Conversations (if logged in).
    Navigates to the corresponding functionality based on user input.
    """
    os.makedirs(saved_login_dir, exist_ok=True)
    print()
    print("Select action:")
    print("1. Register")
    print("2. Log In")
    print("3. Exit")
    if key:
        print("4. Conversations")
    match input(""):
        case "1":
            register()
        case "2":
            login()
        case "3":
            sys.exit()
        case "4":
            if key:
                conversations()
            else:
                print("Please enter a valid number.")
                homepage()
        case _:
            print("Please enter a valid number.")
            homepage()


# --------------------------------------------------------------------------------
# Conversations and Chat Handling
# --------------------------------------------------------------------------------

def conversations():
    """
    Displays the list of active conversations for the logged-in user.
    Allows the user to select a chat to continue or start a new conversation.
    """
    global receiver
    chats_indexed = {}
    print()

    # Fetch conversations from the server
    user_conversations = requests.post(server_config["convo_url"], json={"username": username, "key": key})

    if user_conversations.status_code == 401:
        print("No conversations found!")
        check_user_server()  # Prompt user to start a new conversation
        return

    elif user_conversations.status_code == 200:
        try:
            chats = user_conversations.json()  # Parse JSON safely
            for index, chat in enumerate(chats["chats"]):
                # Split users into a list
                users = chat['users'].split(",")

                # Filter out the logged-in user to get the receiver's name
                receiver = [user for user in users if user != username]

                # If the user has a chat with themselves, set the receiver to their username
                receiver_name = receiver[0] if receiver else username  # If no other user, it means the user is alone in the chat

                # Store the conversation in the indexed list
                chats_indexed[index] = chat
                print(f"{index}: {receiver_name} (Last used: {chat['last_used']})")

            # If no chats are found
            if not chats_indexed:
                print("No conversations found.")
                check_user_server()  # Allow the user to start a new conversation
                return

            # Let the user select the chat
            while True:  # Loop until a valid choice is made
                choice = input("Who would you like to talk to? (Enter index or username): ").strip()

                if choice.isdigit():  # If the user enters an index
                    choice = int(choice)
                    if choice in chats_indexed:
                        choose_chat(chats, chats_indexed, choice)
                        break  # Exit loop if valid choice is made
                    else:
                        print("Invalid index. Please try again.")
                else:  # If the user enters a name
                    choose_chat_by_name(chats_indexed, choice)
                    break  # Exit loop if valid choice by name is made

        except ValueError:
            print("Error parsing server response.")
    elif user_conversations.status_code == 500:
        print("Server side error.")
        homepage()


def choose_chat_by_name(indexed, choice):
    """
    Handles user input to select a chat by name. Searches for a chat with the specified user.
    Sends a request to open the selected chat and displays chat messages.

    Args:
        indexed (dict): Indexed list of conversations for user selection.
        choice (str): The user's input to select a chat by name.
    """
    global receiver
    global username
    response = {}
    receiver = None
    # Iterate over the chats to find a match for the username
    for index, chat in indexed.items():
        if choice in chat["users"]:
            receiver = chat["users"].replace(username, "").strip(",")
            response = requests.post(
                server_config["open_chat_url"], json={"users": f"{username},{receiver}"}
            )
            break
    if receiver is None:
        print("No chat found with that name. Please try again.")
        return  # This will allow the user to make another choice

    if response.status_code == 200:
        response = response.json()
        print(response["chat"])  # Display the chat messages
    elif response.status_code == 400:
        print(response.json()["status"])
    elif response.status_code == 500:
        print("Server error")


def choose_chat(chats, indexed, choice):
    """
    Handles user input to select a chat from the list of conversations.
    Sends a request to open the selected chat and displays chat messages.

    Args:
        chats (dict): The full list of conversations fetched from the server.
        indexed (dict): Indexed list of conversations for user selection.
        choice (int): The user's input to select a chat by index.
    """
    global username
    global receiver
    try:
        if choice in indexed:
            receiver = indexed[choice]["users"].replace(username, "").strip(",")
            response = requests.post(server_config["open_chat_url"], json={"users": f"{username},{receiver}"})
        else:
            print("Invalid index. Please try again.")
            return  # This will allow the user to make another choice
    except ValueError:
        receiver = chats[choice]["users"].replace(username, "").strip(",")
        response = requests.post(server_config["open_chat_url"], json={"users": f"{username},{receiver}"})
        return  # This will allow the user to make another choice

    if response.status_code == 200:
        start_chatting()
    elif response.status_code == 400:
        print(response.json()["status"])
        check_user_server()
        return False
    elif response.status_code == 500:
        print("Server error")

def start_chatting():
    process = multiprocessing.Process(target=retrieve_messages, args=[server_config["open_chat_url"], username, receiver])
    process.start()
    time.sleep(5)
    while True:
        send_msg = input('Your message: ')
        if send_msg:
            requests.post(server_config["send_url"], jsonify({"sender" : username, "receiver" : receiver, "message" : send_msg}))

def retrieve_messages(open_chat_url, user, receive):
    chat : dict = {}
    print("Loading messages...")
    while True:
        response = requests.post(open_chat_url, json={"users": f"{user},{receive}"})
        if response.status_code == 200:
            messages = response.json()["chat"]
            for message_content, message_metadata in messages.items():
                if message_content not in chat and message_metadata["datetime"] not in chat:
                    sender = message_metadata["from"]
                    print(f"[{sender}] {message_content}")
            if messages != chat:
                chat = messages
            time.sleep(10)

def check_user_server():
    """
    Prompts the user to enter the name of a recipient to initiate a new conversation.
    Checks if the recipient exists on the server and creates a new chat if valid.
    """
    global receiver
    receiver = input("Who would you like to talk to? ")
    response = requests.post(server_config["check_user_url"], json={"username": receiver})
    if response.status_code == 401:
        print("No user found with that name.")
        match input("Try again? (y/n)"):
            case "y":
                check_user_server()  # Retry if user wants to
            case _:
                homepage()  # Return to homepage if user opts out
    else:
        response = requests.post(server_config["initiate_conversation_url"], json={"sender": username, "receiver": receiver})
        if response.status_code == 200:
            conversations()  # Refresh the conversation list
        else:
            response= response.json()
            print(response["status"])
            conversations()


# --------------------------------------------------------------------------------
# Login and Registration
# --------------------------------------------------------------------------------

def register():
    """
    Handles user registration by collecting a username and password.
    Sends the information to the server for account creation.
    """
    global username, password

    username = input("Enter a username: ")
    password = input("Enter a password: ")
    repeat_password = input("Repeat the password: ")

    if password == repeat_password and username and password:
        try:
            register_response = requests.post(server_config["register_url"],
                                              json={"username": username, "password": password})

            # Check the register_response status and handle each case
            match register_response.status_code:
                case 200:
                    print("User has been registered!")
                    homepage()
                case 400:
                    server_register_response = register_response.json()  # Extract JSON from the server response
                    print(server_register_response.get("status", "Unknown error"))  # Print "status" field if it exists
                    homepage()
                case _:
                    print(f"Unexpected response from server: {register_response.status_code}")
                    print("Response details:", register_response.text)
        except requests.exceptions.RequestException as error:
            print("Request failed:", error)
    else:
        print("Username or password is empty, please try again.")
        homepage()


def login():
    """
    Handles user login by prompting for credentials or checking saved login.
    Verifies the login with the server and stores the session key upon success.
    """
    global username, password, key
    print()

    # First, attempt to check saved login or ask user
    username = input("Enter your username: ")
    check_login = login_procedure()

    # If no saved login, ask for username and password
    if not check_login:
        username = input("Enter your username: ")
        password = input("Enter your password: ")

    # Proceed with the login attempt
    if username and password:
        login_response = requests.post(server_config["login_url"], json={"username": username, "password": password})
        if login_response.status_code == 200:
            print("Login successful!")
            login_response = login_response.json()
            key = login_response["key"]
            saved = check_saved_login()  # Check again if login is saved
            if not saved:
                save_login()  # Save login if not saved already
            conversations()  # Continue to conversations after successful login

        elif login_response.status_code == 400:
            login_response = login_response.json()
            print(login_response["status"])
            print("Please try again.")
            homepage()  # If login fails, go back to startup

    else:
        print("Please enter a username and password.")
        login()  # If no username or password entered, retry login


def login_procedure():
    """
    Handles the logic for using saved credentials or asking the user for new ones.
    Prompts the user to choose between using saved credentials or entering new ones.

    Returns:
        bool: True if credentials are ready to proceed, False otherwise.
    """
    global username, password

    while True:  # Use a loop to keep asking until valid input is provided
        print()
        choice = input("Use saved password?(y/n): ")
        if choice == "y":
            check_login = check_saved_login()  # Check if the login is saved
            if check_login:
                return True  # Proceed if login is found
            else:
                print("No saved login found, please enter credentials.")  # Only print once
                return False  # Return False if login is not found
        elif choice == "n":
            username = input("Enter your username: ")
            password = input("Enter your password: ")
            return True  # Credentials are entered
        else:
            print("Please type 'y' or 'n'.")  # Continue the loop if invalid input


# --------------------------------------------------------------------------------
# Saved Login Handling
# --------------------------------------------------------------------------------

def save_login():
    """
    Prompts the user to save their login information.
    If the user agrees, the login details are saved to a file.
    """
    global username, password
    print()
    save_log = input("Save login info? (y/n): ")
    match save_log:
        case "y":
            os.makedirs(saved_login_dir, exist_ok=True)
            with open(saved_login_dir + username + ".txt", "w") as f:
                f.write(f"{username},{password}")
                print("Login info saved!")
                conversations()  # Call conversations after saving the login
        case "n":
            conversations()  # Call conversations without saving login
        case _:
            save_login()  # Recurse if invalid input


def check_saved_login():
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


# --------------------------------------------------------------------------------
# Server Connection Utilities
# --------------------------------------------------------------------------------

def check_server_connection(possible_server_urls, client_version):
    """
    Iterates through a list of possible server URLs to establish a connection.
    Sends a "Hello?" message to verify the server's version compatibility.

    Args:
        possible_server_urls (list): List of server URLs to check.
        client_version (str): The current client version for compatibility check.

    Returns:
        str: The first valid server URL if found, otherwise None.
    """
    for url in possible_server_urls:
        try:
            # Send POST request with the "Hello?" message
            response = requests.post(f"{url}/check-connection", timeout=3, json={"message": "Hello?"})

            # Check if the response is valid and matches the client version
            if response.status_code == 200:
                response_json = response.json()
                if response_json.get("server_version") == client_version:
                    return url  # Return the valid server URL
                else:
                    print(f"Version mismatch: Server version {response_json.get('server_version')}, "
                          f"expected {client_version}.")
        except requests.ConnectionError:
            print(f"Failed to connect to {url}.")
            continue  # Try the next URL in the list
        except requests.Timeout:
            print(f"Connection to {url} timed out.")
            continue  # Try the next URL in the list
        except Exception as e:
            print(f"Unexpected error while connecting to {url}: {e}")
            continue  # Handle other exceptions gracefully
    return None  # No valid server found


def configure_urls(base_url):
    """
    Configures a dictionary of server endpoint URLs based on the provided base URL.

    Args:
        base_url (str): The base URL of the server.

    Returns:
        dict: A dictionary containing the configured endpoint URLs.
    """
    return {
        "base_url": base_url,
        "send_url": f"{base_url}/send",
        "login_url": f"{base_url}/login",
        "register_url": f"{base_url}/register",
        "convo_url": f"{base_url}/convo",
        "check_user_url": f"{base_url}/check-user-exists",
        "initiate_conversation_url": f"{base_url}/initiate-conversation",
        "open_chat_url": f"{base_url}/open-convo"
    }


# --------------------------------------------------------------------------------
# Client Startup
# --------------------------------------------------------------------------------

def start_client():
    """
    Initializes the chat client by attempting to connect to a server.
    If a valid server is found, configures server URLs and navigates to the homepage.
    If no server is reachable, prompts the user to retry or exit.
    """
    global server_config
    client_version = "pre-alpha V0.9.0"  # Current client version
    possible_server_urls = [
        #"http://fortbow.duckdns.org:5000",
        #"http://172.27.27.231:5000",
        "http://127.0.0.1:5000"
    ]

    while True:
        # Check for a valid server connection
        server_url = check_server_connection(possible_server_urls, client_version)

        if server_url:
            print(f"Connected to server at {server_url}")

            # Configure the server URLs for further usage
            server_config = configure_urls(server_url)

            # Move to the main application entry point
            homepage()
            break
        else:
            # Retry or exit if no valid server is found
            if input("No reachable server URL found. Try again? (y/n): ").lower() != 'y':
                sys.exit()


# --------------------------------------------------------------------------------
# Program Entry Point
# --------------------------------------------------------------------------------

if __name__ == "__main__":
    """
    The entry point of the application. Starts the client by initializing server connection
    and navigating to the main homepage.
    """
    start_client()