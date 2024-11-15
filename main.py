import sys
import requests
from datetime import date
import os
from rich import print

# import subprocess

client_version = "v0.5.3"
server_base_url = ""
send_url = server_base_url + "/send"
login_url = server_base_url + "/login"
register_url = server_base_url + "/register"
convo_url = server_base_url + "/convo"
check_user_url = server_base_url + "/check-user-exists"
initiate_conversation_url = server_base_url + "/initiate-conversation"
open_chat_url = server_base_url + "/open-convo"
                    
username = ""
password = ""
receiver = ""
key = ""
saved_login_dir = os.getenv("USERPROFILE") + "/Documents/PythonChatApp/Saved-Profiles/"
current_date = date.today().strftime("%Y-%m-%d")


# options, send, login, register, receive
#
#
#
#

def homepage():
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
    return


def conversations():
    global receiver
    chats_indexed = {}
    print()
    user_conversations = requests.post(convo_url, json={"username": username, "key": key})
    if user_conversations.status_code == 401:
        print("No conversations found!")
        check_user_server()
    elif user_conversations.status_code == 200:
        chats = user_conversations.json()
        i = 0
        for index,chat in enumerate(chats):
            chats_indexed[index] = chat
            print(index,chat)
        choice = input("Who would you like to talk to? ")
        choose_chat(chats, chats_indexed, choice)
    elif user_conversations.status_code == 500:
        print("Server side error.")

def choose_chat(chats, indexed, choice):
    try:
        choice = int(choice)
        response = requests.post(open_chat_url, json=(indexed[choice]))
    except (ValueError, KeyError):
        response = requests.post(open_chat_url, json=(chats[choice]))
    if response:
        if response.status_code == 200:
            response = response.json()
        elif response.status_code == 400:
            response = response.json()
            choice = input(response["status"])
            choose_chat(chats, indexed, choice)
        elif response.status_code == 500:
            print("Server error")

def check_user_server():
    global receiver
    receiver = input("Who would you like to talk to? ")
    response = requests.post(check_user_url, json={"username" : receiver})
    if response.status_code == 401:
        print("No user found with that name.")
        match input("Try again? (y/n)"):
            case "y":
                check_user_server()
            case _:
                homepage()
    else:
        requests.post(initiate_conversation_url, json={"sender" : username, "receiver" : receiver})
        conversations()


def save_login():
    print()
    global username
    global password

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
    global username
    global password
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


def login_procedure():
    global username
    global password

    while True:  # Use a loop to keep asking until valid input is provided
        print()
        # Prompt user whether they want to use saved password
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
            return True  # Return False and move to enter credentials
        else:
            print("Please type 'y' or 'n'.")  # Continue the loop if invalid input


def login():
    global username
    global password
    global key
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
        login_response = requests.post(login_url, json={"username": username, "password": password})
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


def register():
    global username
    global password

    username = input("Enter a username: ")
    password = input("Enter a password: ")
    repeat_password = input("Repeat the password: ")

    if password == repeat_password and username and password:
        try:
            register_response = requests.post(register_url, json={"username": username, "password": password})

            # Check the register_response status and handle each case
            match register_response.status_code:
                case 200:
                    print("User Has been registered!")
                    homepage()
                case 400:
                    # Handle 400 register_response and print server message
                    server_register_response = register_response.json()  # Extract JSON from the server register_response
                    print(server_register_response.get("status", "Unknown error"))  # Print "status" field if it exists
                    homepage()
                case _:
                    # Handle unexpected status codes
                    print(f"Unexpected register_response from server: {register_response.status_code}")
                    print("register_response details:", register_response.text)
        except requests.exceptions.RequestException as error:
            print("Request failed:", error)
    else:
        print("Username or password is empty, please try again.")
        homepage()



def start_client():
    global send_url
    global login_url
    global register_url
    global convo_url
    global check_user_url
    global initiate_conversation_url
    global server_base_url
    global open_chat_url

    server_base_url = ""
    print("Checking connection with the server, please hold...")
    possible_server_urls = [
        "http://fortbow.duckdns.org:5000",
        "http://172.27.27.231:5000",
        "http://127.0.0.1:5000"
    ]
    main_response = ""
    for url in possible_server_urls:
        try:
            # Try connecting to the server with a small timeout
            main_response = requests.post(url + "/check-connection", timeout=1, json={"message": "Hello?"})
            if main_response.status_code == 200:
                response_json = main_response.json()
                if response_json["server_version"] == client_version:
                    print("Connection with server established!")
                    server_base_url = url
                    send_url = server_base_url + "/send"
                    login_url = server_base_url + "/login"
                    register_url = server_base_url + "/register"
                    convo_url = server_base_url + "/convo"
                    check_user_url = server_base_url + "/check-user-exists"
                    initiate_conversation_url = server_base_url + "/initiate-conversation"
                    open_chat_url = server_base_url + "/open-convo"
                    while True:
                        homepage()
                else:
                    print("Server and client version do not match, please download the newest version!")
                    break
        except requests.ConnectionError:
            # If connection fails, continue to the next URL
            continue
    if main_response and main_response.status_code == 200:
        homepage()
    else:
        print("No reachable server URL found.")
        match input("Try again(y/n): "):
            case "y:":
                start_client()
            case _:
                sys.exit()



if __name__ == "__main__":
    start_client()