import requests
from datetime import date
import os

# Base server URL
server_base_url = "http://172.27.27.231:5000"

# Endpoint paths
send_url = server_base_url + "/send"
login_url = server_base_url + "/login"
register_url = server_base_url + "/register"
convo_url = server_base_url + "/register"

sender = "ScitechMC"
username = ""
password = ""
receiver = "nig"
saved_login_dir = os.getenv("USERPROFILE") + "/Documents/PythonChatApp/Saved-Profiles"

try:
    r = requests.get(server_ip)
    print(r.text)  # Print the content of the response
except requests.exceptions.RequestException as e:
    print("Request failed:", e)

choice = input("send(s)/or receive(r): ")
match choice:
    case "s":
        send_message = input("Please enter text to send to the server: ")
        try:
            # Convert the date object to a string (YYYY-MM-DD)
            current_date = date.today().strftime("%Y-%m-%d")
            # Send the message in JSON format
            r = requests.post(send_url, json={
                "message": send_message,
                "sender": sender,
                "receiver": receiver,
                "date": current_date  # Use the current_date string here, not the 'date' class
            })
            print("Server response:", r.text)  # Print the server's response
        except requests.exceptions.RequestException as e:
            print("Request failed:", e)
    case "r":
        try:
            r = requests.get(server_ip_receive)
            print(r.text)  # Print the content of the response
        except requests.exceptions.RequestException as e:
            print("Request failed:", e)



#options, send, login, register, receive
#
#
#
#
#
#
#
#
#
def homepage():
    print("1. Register")
    print("2. Log In")
    match input("")
        case "1":
            register()
        case "2":
            login()
        case _:
            print("Please enter a number(1/2)")
            homepage()
    return
    
def conversations():
    requests.POST
def login():
    match input("Use saved password?(y/n)"):
        case
        sender = input("Enter your username: ")
        password = input("Enter your password: ")
        if sender and password:
            logged_in = requests.POST(login_url, json={"username" = sender, "password" = password})
            if logged_in == "True":
                print("You are logged in!")
                homepage()
            if logged_in == "Account exists":
                print("That account already exist!")
                homepage()
            
def save_login():
    save_log = input("Save login info? (y/n): ")
    match save_log:
        case "y":
            os.makedir(saved_login_dir, exist_ok=True)
            with open(saved_login_dir+username+".txt", "w") as f:
                f.write(f"{username},{password}")
        case "n":
            homepage()
        case _:
            save_login()            
def register():
    username = input("Enter a username: ")
    password = input("Enter a password: ")
    repeat_password = input("Repeat the password: ")
    if password == repeat_password:
        signed_in = requests.POST(register_url, json={"username" = username, "password" = password})
        match signed_in:
            case "True":
                print("You are signed in!")
                homepage()
    else:
        print("Username or password is empty, please try again.")
        homepage()