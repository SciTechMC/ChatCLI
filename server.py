import random
import string

from flask import Flask, request, jsonify
import os
import json
from datetime import date
from datetime import datetime
from rich import print

server_version = "pre-alpha V0.7.0"

app = Flask(__name__)

@app.route("/check-connection", methods=["GET", "POST"])
def check_connection():
    os.makedirs("connection-checks", exist_ok=True)
    data = request.get_json(silent=True)  # Use silent=True to avoid errors if no JSON is sent
    if data and data["message"] == "Hello?":
        current_date = date.today().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")
        client_ip = request.remote_addr
        with open(f"connection-checks/{current_date}.txt", "a") as f:
            f.write(f"{client_ip}   {current_time}\n")
        return jsonify({"status": "Hello World", "server_version": server_version}), 200
    else:
        return jsonify({"error": "Bad Request"}), 400

@app.route("/open-convo", methods=["GET" ,"POST"])
def return_user_chat():
    data = request.get_json()
    chats = os.listdir("messages")
    user1, user2 = data["users"].split(",")
    for chat in chats:
        if user1 in chat and user2 in chat:
            with open(chat, "r") as f:
                return json.load(f)

def save_key(username, key):
    file_path = "keys.json"
    try:
        # Try loading existing data if the file exists
        with open(file_path, "r") as keyfile:
            data = json.load(keyfile)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file does not exist or has invalid JSON, start with an empty dictionary
        data = {}

    # Update data by adding or replacing the key for the username
    data[username] = key

    # Write the updated data back to the file
    with open(file_path, "w") as keyfile:
        json.dump(data, keyfile, indent=4)

@app.route("/initiate-conversation", methods=["GET", "POST"])
def initiate_conversation():
    req_data = request.get_json()
    file_path = "messages/chats.json"

    # Attempt to read existing data, if any
    try:
        with open(file_path, "r") as chatsfile:
            data = json.load(chatsfile)  # Attempt to load JSON content
    except (FileNotFoundError, json.JSONDecodeError):
        # If file does not exist or contains invalid JSON, start with an empty dictionary
        data = {}

    # Prepare new conversation data
    current_date = date.today().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")

    # Create a unique key based on sender and receiver
    data[req_data["sender"] + "--" + req_data["receiver"]] = {
        "users": f"{req_data['sender']},{req_data['receiver']}",
        "last_used": f"{current_date} {current_time}",
        "initiated": f"{current_date} {current_time}",
    }

    # Write the updated data back to the file
    with open(file_path, "w") as chatsfile:
        json.dump(data, chatsfile, indent=4)

@app.route("/send", methods=["GET", "POST"])
def sent_message():
    os.makedirs("messages", exist_ok=True)

    # Receive message
    data = request.get_json()  # Use .get_json() if the client sends JSON data
    if data and "message" in data and "sender" in data and "receiver" in data:
        message = data["message"]
        sender = data["sender"]
        receiver = data["receiver"]
        if os.path.exists(f"users/{receiver}.txt"):  # Check if the receiver exists in the userbase
            file_path = os.path.join("messages", f"{sender} -- {receiver}.txt")
            with open(file_path, "a") as f:
                f.write(f"<{sender}> {message}\n")  # Add newline for clarity
            return jsonify({"status": "Message sent!"}), 200
        else:
            return jsonify({"status": "Receiver not found"}), 400
    return jsonify({"status": "Invalid message data"}), 400

@app.route("/login", methods=["GET", "POST"])
def login():
    os.makedirs("users", exist_ok=True)

    # Checks if user is in userbase and checks if passwords match
    data = request.get_json()  # Use .get_json() if the client sends JSON data
    if data and "username" in data and "password" in data:
        file_path = os.path.join("users", f"{data['username']}.txt")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                stored_password = f.read().strip()  # Read the stored password and remove any trailing spaces/newlines
                if stored_password == data["password"]:
                    gen_key = str(
                        ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8)))
                    save_key(data["username"], gen_key)
                    return jsonify({"status": "Login successful!", "key": gen_key}), 200
                else:
                    return jsonify({"status": "Incorrect password"}), 400
        else:
            return jsonify({"status": "User not found"}), 400
    return jsonify({"status": "Invalid login data"}), 400

@app.route("/register", methods=["GET", "POST"])
def register():
    os.makedirs("users", exist_ok=True)

    data = request.get_json()  # Use .get_json() if the client sends JSON data
    if data and "username" in data and "password" in data:
        file_path = os.path.join("users/", f"{data['username']}.txt")
        if os.path.exists(file_path):
            return jsonify({"status": "Username already taken"}), 400
        with open(file_path, 'w') as f:
            f.write(data["password"])  # Store the password in the file
        return jsonify({"status": "User created successfully!"}), 200
    return jsonify({"status": "Invalid signup data"}), 400

@app.route("/convo", methods=["GET", "POST"])
def conversations():
    # Get the request data (username)
    request_data = request.get_json()
    os.makedirs("messages", exist_ok=True)

    # Try to load existing chat data from the file
    try:
        with open("messages/chats.json", 'r') as chatsfile:
            chat_data = json.load(chatsfile)  # Load JSON data into a dictionary
    except (FileNotFoundError, json.JSONDecodeError):
        chat_data = {}  # Start with an empty dictionary if the file is missing or corrupt

    # Prepare a result dictionary for storing relevant conversations
    result = {}

    # Iterate over the chat data
    for key, conversation in chat_data.items():
        # Extract usernames from the key
        user1, user2 = key.split("--")

        # Check if the current user is involved in this conversation
        if user1 == request_data["username"]:
            result[user2] = conversation
        elif user2 == request_data["username"]:
            result[user1] = conversation

    # Return the filtered conversations or an appropriate message
    if result:
        return jsonify(result), 200
    else:
        return jsonify({"status": "None"}), 401

@app.route("/check-user-exists", methods=["GET", "POST"])
def check_user_exists():
    data = request.get_json()
    if data and data["username"]:
        if os.path.exists(f"users/{data['username']}.txt"):
            return jsonify({"status" : "Valid user"}), 200
        else:
            return  jsonify({"status" : "Invalid user"}), 400

if __name__ == "__main__":
    print(f"   * [red]SERVER VERSION: {server_version}[/]")
    app.run(host="0.0.0.0", debug=True)