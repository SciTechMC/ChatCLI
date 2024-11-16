import random
import string
from flask import Flask, request, jsonify
import os
import json
from datetime import date
from datetime import datetime
from rich import print

server_version = "pre-alpha V0.8.0"
app = Flask(__name__)

# ------------------------------------------------------------------------------------------------
# Route: /check-connection
# Description: Handles client connection checks and logs the connection attempt with the client's IP address
# ------------------------------------------------------------------------------------------------
@app.route("/check-connection", methods=["GET", "POST"])
def check_connection():
    """
    Endpoint for checking the connection to the server. It logs the IP address and timestamp of the client attempting to connect.

    - If the client sends a message "Hello?", the server responds with a success message and logs the connection.
    - If the message is not "Hello?", the server responds with an error (400 Bad Request).

    Returns:
        - 200: If the "Hello?" message is received, responds with the current server version and success status.
        - 400: If the message is not "Hello?", responds with a "Bad Request" error message.
    """
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

# ------------------------------------------------------------------------------------------------
# Route: /open-convo
# Description: Retrieves an existing conversation between two users, if available
# ------------------------------------------------------------------------------------------------
@app.route("/open-convo", methods=["GET" ,"POST"])
def return_user_chat():
    """
    Endpoint for retrieving a conversation between two users. It checks if a chat file exists for the specified users.

    - Accepts a JSON body with the users' names.
    - Returns the chat content if the file for those users exists.
    - If the chat file doesn't exist or data is invalid, it returns an error message.

    Returns:
        - 200: If a chat is found, responds with the chat content.
        - 400: If no chat is found or if the input data is invalid.
    """
    data = request.get_json()
    chats = os.listdir("messages")
    if chats and data:
        user1, user2 = data["users"].split(",")
        for chat in chats:
            if user1 in chat and user2 in chat and chat:
                try:
                    with open(os.path.join("messages", chat), "r") as f:
                        chat_data = json.load(f)
                        return jsonify({"chat": chat_data})
                except (json.JSONDecodeError, FileNotFoundError):
                    return jsonify({"status": "Chat data corrupted or not found."}), 400
        return jsonify({"status": "No chat found"}), 400
    else:
        return jsonify({"status": "Data invalid"}), 400

# ------------------------------------------------------------------------------------------------
# Function: save_key
# Description: Saves the generated key for a user to a JSON file
# ------------------------------------------------------------------------------------------------
def save_key(username, key):
    """
    Saves the generated key for the user into a JSON file.

    - Attempts to read an existing keys file.
    - If the file doesn't exist or is invalid, it starts with an empty dictionary.
    - Adds or updates the key for the user and writes it back to the file.

    Arguments:
        - username: The username for which the key is being saved.
        - key: The key that will be saved for the user.
    """
    file_path = "keys.json"
    try:
        with open(file_path, "r") as keyfile:
            data = json.load(keyfile)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    data[username] = key

    with open(file_path, "w") as keyfile:
        json.dump(data, keyfile, indent=4)

# ------------------------------------------------------------------------------------------------
# Route: /initiate-conversation
# Description: Initiates a new conversation between two users and logs the conversation details
# ------------------------------------------------------------------------------------------------
@app.route("/initiate-conversation", methods=["GET", "POST"])
def initiate_conversation():
    """
    Endpoint for initiating a conversation between two users.

    - Accepts a JSON body with sender and receiver details.
    - Logs the conversation initiation with timestamps and saves it to a file.
    - Returns a success message upon successful initiation.

    Returns:
        - 200: If the conversation is successfully initiated.
        - 400: If there are any errors during the process.
    """
    req_data = request.get_json()
    file_path = "messages/chats.json"

    try:
        with open(file_path, "r") as chatsfile:
            data = json.load(chatsfile)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    current_date = date.today().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")

    data[req_data["sender"] + "--" + req_data["receiver"]] = {
        "users": f"{req_data['sender']},{req_data['receiver']}",
        "last_used": f"{current_date} {current_time}",
        "initiated": f"{current_date} {current_time}",
    }

    with open(file_path, "w") as chatsfile:
        json.dump(data, chatsfile, indent=4)

# ------------------------------------------------------------------------------------------------
# Route: /send
# Description: Sends a message between two users and stores it in a file
# ------------------------------------------------------------------------------------------------
@app.route("/send", methods=["GET", "POST"])
def sent_message():
    """
    Endpoint for sending a message from one user to another.

    - Accepts a JSON body with the sender, receiver, and message content.
    - Validates the existence of the receiver in the user base before saving the message.
    - Stores the message in a text file for each sender-receiver pair.

    Returns:
        - 200: If the message is sent successfully.
        - 400: If the receiver is not found or the message data is invalid.
    """
    os.makedirs("messages", exist_ok=True)

    data = request.get_json()
    if data and "message" in data and "sender" in data and "receiver" in data:
        message = data["message"]
        sender = data["sender"]
        receiver = data["receiver"]
        if os.path.exists(f"users/{receiver}.txt"):
            file_path = os.path.join("messages", f"{sender} -- {receiver}.txt")
            with open(file_path, "a") as f:
                f.write(f"<{sender}> {message}\n")
            return jsonify({"status": "Message sent!"}), 200
        else:
            return jsonify({"status": "Receiver not found"}), 400
    return jsonify({"status": "Invalid message data"}), 400

# ------------------------------------------------------------------------------------------------
# Route: /login
# Description: Handles user login, validating credentials and generating a session key
# ------------------------------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Endpoint for user login. Validates username and password, and generates a session key.

    - Accepts a JSON body with username and password.
    - Checks if the username exists and if the password matches the stored password.
    - If valid, generates a session key and saves it to a file.

    Returns:
        - 200: If login is successful, responds with a session key.
        - 400: If the username or password is invalid.
    """
    os.makedirs("users", exist_ok=True)

    data = request.get_json()
    if data and "username" in data and "password" in data:
        file_path = os.path.join("users", f"{data['username']}.txt")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                stored_password = f.read().strip()
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

# ------------------------------------------------------------------------------------------------
# Route: /register
# Description: Registers a new user with a username and password
# ------------------------------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Endpoint for registering a new user.

    - Accepts a JSON body with username and password.
    - Checks if the username is already taken. If not, it stores the username and password in a file.

    Returns:
        - 200: If registration is successful.
        - 400: If the username is already taken or the signup data is invalid.
    """
    os.makedirs("users", exist_ok=True)

    data = request.get_json()
    if data and "username" in data and "password" in data:
        file_path = os.path.join("users/", f"{data['username']}.txt")
        if os.path.exists(file_path):
            return jsonify({"status": "Username already taken"}), 400
        with open(file_path, 'w') as f:
            f.write(data["password"])
        return jsonify({"status": "User created successfully!"}), 200
    return jsonify({"status": "Invalid signup data"}), 400

# ------------------------------------------------------------------------------------------------
# Route: /convo
# Description: Retrieves all conversations for a specific user
# ------------------------------------------------------------------------------------------------
@app.route("/convo", methods=["GET", "POST"])
def conversations():
    """
    Endpoint for retrieving conversations associated with a specific user.

    - Accepts a JSON body with the username.
    - Returns the conversations where the user is involved.

    Returns:
        - 200: If conversations are found for the user.
        - 401: If no conversations are found.
    """
    request_data = request.get_json()
    os.makedirs("messages", exist_ok=True)

    try:
        with open("messages/chats.json", 'r') as chatsfile:
            chat_data = json.load(chatsfile)
    except (FileNotFoundError, json.JSONDecodeError):
        chat_data = {}

    result = []  # Store multiple conversations

    for key, conversation in chat_data.items():
        user1, user2 = key.split("--")
        if user1 == request_data["username"] or user2 == request_data["username"]:
            result.append({
                "key": key,
                "users": conversation["users"],
                "last_used": conversation["last_used"],
                "initiated": conversation["initiated"]
            })

    if result:
        return jsonify({"chats": result}), 200
    else:
        return jsonify({"status": "None"}), 401

# ------------------------------------------------------------------------------------------------
# Route: /check-user-exists
# Description: Checks if a user exists in the userbase
# ------------------------------------------------------------------------------------------------
@app.route("/check-user-exists", methods=["GET", "POST"])
def check_user_exists():
    """
    Endpoint for checking if a user exists.

    - Accepts a JSON body with the username.
    - Returns a valid status if the user exists, and an error if the user doesn't exist.

    Returns:
        - 200: If the user exists in the userbase.
        - 400: If the user does not exist.
    """
    data = request.get_json()
    if data and data["username"]:
        if os.path.exists(f"users/{data['username']}.txt"):
            return jsonify({"status": "Valid user"}), 200
        else:
            return jsonify({"status": "Invalid user"}), 400

# ------------------------------------------------------------------------------------------------
# Main entry point: Starts the Flask server
# ------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"   * [red]SERVER VERSION: {server_version}[/]")
    app.run(host="0.0.0.0", debug=True)
