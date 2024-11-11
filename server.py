from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "Hello World"

@app.route("/send", methods=["POST"])
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
            return jsonify({"status": "Receiver not found"}), 404
    return jsonify({"status": "Invalid message data"}), 400

@app.route("/login", methods=["POST"])
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
                    return jsonify({"status": "Login successful!"}), 200
                else:
                    return jsonify({"status": "Incorrect password"}), 401
        else:
            return jsonify({"status": "User not found"}), 404
    return jsonify({"status": "Invalid login data"}), 400

@app.route("/signup", methods=["POST"])
def signup():
    os.makedirs("users", exist_ok=True)

    data = request.get_json()  # Use .get_json() if the client sends JSON data
    if data and "username" in data and "password" in data:
        file_path = os.path.join("users", f"{data['username']}.txt")
        if os.path.exists(file_path):
            return jsonify({"status": "Username already taken"}), 400
        with open(file_path, 'w') as f:
            f.write(data["password"])  # Store the password in the file
        return jsonify({"status": "User created successfully!"}), 201
    return jsonify({"status": "Invalid signup data"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0")