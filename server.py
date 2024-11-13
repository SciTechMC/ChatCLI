import random
import string
from flask import Flask, request, jsonify
import os
import json
from datetime import date
from datetime import datetime

server_version = "v0.2.0"

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
        return jsonify({"status": "Hello World", "server_version" : server_version"}), 200
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
                    gen_key = str(''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8)))
                    logged_in = save_key(data["username"], gen_key)
                    return jsonify({"status": "Login successful!", "key" : gen_key}), 200
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
    user_chats : list

    os.makedirs("messages", exist_ok=True)
    try:
        open("messages/convos.json", 'x')
    finally:
        with open("messages/convos.json", 'r') as convos:
            all_chats = convos.read()
    
    for conversation in all_chats:
        if conversation["user1"] == data["username"]:
            user_chats += [conversation["user2"]]
        elif conversations["user2"] == data["username"]:
            user_chats += [conversation["user1"]]




if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)