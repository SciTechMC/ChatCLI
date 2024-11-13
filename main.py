import requests
from datetime import date
import os
from rich import print

# Base server URL
server_base_url = "http://172.27.27.231:5000"

# Endpoint paths
send_url = server_base_url + "/send"
login_url = server_base_url + "/login"
register_url = server_base_url + "/register"
convo_url = server_base_url + "/convo"
client_version = "v0.2.0"

username = ""
password = ""
receiver = ""
key = ""
saved_login_dir = os.getenv("USERPROFILE") + "/Documents/PythonChatApp/Saved-Profiles/"
current_date = date.today().strftime("%Y-%m-%d")

#options, send, login, register, receive
#
#
#
#

def homepage():
    os.makedirs(saved_login_dir, exist_ok=True)
    print("1. Register")
    print("2. Log In")
    match input(""):
        case "1":
            register()
        case "2":
            login()
        case "3":
            conversations()
        case _:
            print("Please enter a number(1/2)")
            homepage()
    return
    
def conversations():
    convos = requests.post(convo_url, json={"username" : username, "key" : key})
    #for "chat" in convos:
    #    print(f" ({date})")
    print(convos)

def save_login():
    global username
    global password

    save_log = input("Save login info? (y/n): ")
    match save_log:
        case "y":
            os.makedirs(saved_login_dir, exist_ok=True)
            with open(saved_login_dir+username+".txt", "w") as f:
                f.write(f"{username},{password}")
                conversations()
        case "n":
            conversations()
        case _:
            save_login()

def check_saved_login(option):
    global username
    global password
    file_list = []
    if os.listdir(saved_login_dir):
        for file in os.listdir(saved_login_dir):
            file_list += [file]
            if file.endswith(".txt") and len(file_list) == 1:
                with open(os.path.join(saved_login_dir, file), "r") as f:
                    if option == "check" and [username, password] == f.read().split(","):
                        return True
                    else:
                        username, password = f.read().split(",")
    else:
        if option == "check":
            return False
        else:
            print("No user login has been saved.")
        login()
    if len(file_list) > 1:
        choice = input("Please enter the username you would like to sign in with: ")
        if os.path.exists(saved_login_dir + choice):
            with open(os.path.join(saved_login_dir, choice), "r") as f:
                username, password = f.read().split(",")

        else:
            print("That username's login info is not saved.")
            login()

def login():
    global username
    global password
    global key

    match input("Use saved password?(y/n)"):
        case "y":
            check_saved_login("")

        case "n":
            username = input("Enter your username: ")
            password = input("Enter your password: ")
        case _:
            print("Please type 'y' or 'n'.")
            login()
    if username and password:
        response = requests.post(login_url, json={"username" : username, "password" : password})
        if response.status_code == 200:
            print("Login successful!")
            response = response.json()
            key = response["key"]
            saved = check_saved_login("check")
            if not saved:
                save_login()
            conversations()

        elif response.status_code == 400:
            response = response.json()
            print(response["status"])
            print("Please try again.")
            homepage()

def register():
    global username
    global password

    username = input("Enter a username: ")
    password = input("Enter a password: ")
    repeat_password = input("Repeat the password: ")

    if password == repeat_password and username and password:
        try:
            response = requests.post(register_url, json={"username": username, "password": password})

            # Check the response status and handle each case
            match response.status_code:
                case 200:
                    print("User Has been registered!")
                    homepage()
                case 400:
                    # Handle 400 response and print server message
                    server_response = response.json()  # Extract JSON from the server response
                    print(server_response.get("status", "Unknown error"))  # Print "status" field if it exists
                    homepage()
                case _:
                    # Handle unexpected status codes
                    print(f"Unexpected response from server: {response.status_code}")
                    print("Response details:", response.text)
        except requests.exceptions.RequestException as error:
            print("Request failed:", error)
    else:
        print("Username or password is empty, please try again.")
        homepage()

if __name__ == "__main__":
    print("Checking connection with the server, please hold...")
    try:
        r = requests.post(server_base_url + "/check-connection", json={"message" : "Hello?"})
        if r.status_code == 200:
            r = r.json()
            if r["server_version"] == client_version:
                homepage()
        else:
            print(f"[red]Unable to connect to server. Status code: {r.status_code}[/red]")
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)