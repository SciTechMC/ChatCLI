from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route("/check-connection", methods=["GET", "POST"])
def hello_world():
    print("nigger")
    data = request.get_json(silent=True)  # Use silent=True to avoid errors if no JSON is sent
    if data and data["message"] == "Hello?":
        return jsonify({"status": "Hello World"}), 200
    else:
        return jsonify({"error": "Bad Request"}), 400

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
                    return jsonify({"status": "Login successful!"}), 200
                else:
                    return jsonify({"status": "Incorrect password"}), 400
        else:
            return jsonify({"status": "User not found"}), 400
    return jsonify({"status": "Invalid login data"}), 400

@app.route("/register", methods=["GET", "POST"])
def register():
    print("nugger")
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)