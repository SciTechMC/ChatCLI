import random
import string
from flask import Flask, request, jsonify
import os
import json
from datetime import date
from datetime import datetime

server_version = "v0.5.3"

app = Flask(__name__)


@app.route("/check-connection", methods=["GET", "POST"])
def hello_world():
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
    data = {}

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
        "initiated": f"{current_date} {current_time}"
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
    data = request.get_json()
    os.makedirs("messages", exist_ok=True)
    try:
        with open("messages/chats.json", 'r') as chatsfile:
            json.load(chatsfile)
    except (FileNotFoundError, json.JSONDecodeError):
        open("messages/chats.json", 'x')
        data = {}

    for conversation in data:
        user1, user2 = conversation["users"].split(",")
        if user1 == data["username"]:
            data[user2] = conversation
        elif user2 == data["username"]:
            data[user1] = conversation
    if data:
        return jsonify(data), 200
        
    else:
        return jsonify({"status" : "None"}), 401

@app.route("/check-user-exists", methods=["GET", "POST"])
def check_user_exists():
    data = request.get_json()
    if data and data["username"]:
        if os.path.exists(f"users/{data['username']}.txt"):
            return jsonify({"status" : "Valid user"}), 200
        else:
            return  jsonify({"status" : "Invalid user"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)