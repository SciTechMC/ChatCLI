import mysql.connector
import random
import string
from flask import Flask, request, jsonify, g
import re
from waitress import serve

app = Flask(__name__)

#gunicorn --workers 4 --bind 0.0.0.0:5000 server_flask:app

# ---------------------------- DATABASE UTILITIES ----------------------------

def get_db():
    """
    :return: A MySQL database connection stored in Flask's 'g' object.
    """
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host="localhost",
            user="production_chatcli",
            password="S3cret#Code1234",
            database="chatcli_prod"
        )
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """
    Ensures the database connection is closed after each request.
    :param exception: Any exception raised during the request.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

# ---------------------------- UTILITY FUNCTIONS ----------------------------

def verif_user(username, user_key):
    """
    :param username: The client's username
    :param user_key: The key that the client has sent to the server
    :return: True or False depending on the user validity
    """
    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_key FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        return user and user["user_key"] == user_key
    except mysql.connector.Error:
        return False
    finally:
        cursor.close()

def return_statement(response=None, error="", status_code=200, additional=None):
    """
    :param response: The data to be sent back to the client.
    :param error: The error message.
    :param status_code: HTTP status code for the response.
    :param additional: Additional data as a dictionary.
    :return: A JSON response with appropriate fields.
    """
    return jsonify({
        "response": response,
        "error": error,
        **(dict([additional]) if additional else {})
    }), status_code

# ---------------------------- ROUTES ----------------------------

@app.route("/verify-connection", methods=["POST", "GET"])
def verify_connection():
    """
    Test route to verify server is reachable.
    """
    return return_statement(response="Hello World!")

@app.route("/register", methods=["POST", "GET"])
def register():
    """
    Registers a new user in the system.
    :return: Success or error message depending on input and database state.
    """
    client = request.get_json()
    username = client.get("username", "").lower()
    password = client.get("password", "")
    email = client.get("email", "")

    # Validate input fields
    if not username or not password:
        return return_statement("", "Username and password are required", 400)
    if any(char in r'"%\'()*+,/:;<=>?@[\]^{|}~` ' for char in username):
        return return_statement("", "Username includes bad characters", 400)
    if any(char in r'";\ ' for char in password):
        return return_statement("", "Password includes bad characters", 400)
    if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
        return return_statement("", "Invalid email address", 400)

    cursor = get_db().cursor()
    try:
        # Check if the user already exists
        cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return return_statement("", f"User '{username}' already exists", 400)

        # Insert the new user
        cursor.execute(
            "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)",
            (username, password, email)
        )
        get_db().commit()
        return return_statement(f"User '{username}' registered successfully!")
    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor.close()

@app.route("/login", methods=["POST", "GET"])
def login():
    """
    Logs in a user by validating credentials and generating a session key.
    :return: Login success message or error.
    """
    client = request.get_json()
    username = client.get("username", "").lower()
    password = client.get("password", "")

    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute("SELECT userID, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if not user:
            return return_statement("", "Username not found!", 404)
        if user["password"] != password:
            return return_statement("", "Invalid password", 400)

        # Generate a session key
        user_key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=24))
        cursor.execute("UPDATE users SET user_key = %s WHERE userID = %s", (user_key, user["userID"]))
        get_db().commit()
        return return_statement("Login Successful!", additional=["user_key", user_key])
    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor.close()

@app.route("/fetch-chats", methods=["POST", "GET"])
def fetch_chats():
    """
    Fetches chat participants for a user.
    :return: List of usernames involved in chats with the user.
    """
    client = request.get_json()
    username = client.get("username", "").lower()
    user_key = client.get("user_key", "")

    if not verif_user(username, user_key):
        return return_statement("", "Unable to verify user!", 400)

    cursor = get_db().cursor()
    try:
        cursor.execute("""
        SELECT DISTINCT u.username
        FROM users u
        JOIN participants p ON u.userID = p.userID
        WHERE p.chatID IN (
            SELECT chatID FROM participants
            WHERE userID = (SELECT userID FROM users WHERE username = %s)
        ) AND u.userID != (SELECT userID FROM users WHERE username = %s)
        """, (username, username))
        chats = [row[0] for row in cursor.fetchall()]
        return return_statement(chats)
    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor.close()

@app.route("/create-chat", methods=["POST", "GET"])
def create_chat():
    client = request.get_json()
    username = client.get("username").lower()
    receiver = client.get("receiver").lower()
    user_key = client.get("user_key")

    if not username or not receiver:
        return return_statement("", "Some statements are empty", 404)

    # Verify user
    if not verif_user(username, user_key):
        return return_statement("", "Unable to verify user!", 400)

    cursor_create_chat = get_db().cursor()

    try:
        # Start a transaction
        cursor_create_chat.execute("START TRANSACTION;")

        # Get user IDs for participants
        cursor_create_chat.execute("SELECT userID FROM Users WHERE LOWER(username) = %s;", (username,))
        sender_id = cursor_create_chat.fetchone()

        cursor_create_chat.execute("SELECT userID FROM Users WHERE LOWER(username) = %s;", (receiver,))
        receiver_id = cursor_create_chat.fetchone()

        # Check if sender or receiver exist
        if not sender_id or not receiver_id:
            return return_statement("", "Sender or receiver not found!", 400)

        sender_id = sender_id[0]
        receiver_id = receiver_id[0]

        # Create a new chat
        cursor_create_chat.execute("INSERT INTO Chats () VALUES ();")

        # Retrieve the new chatID
        cursor_create_chat.execute("SELECT LAST_INSERT_ID();")
        chat_id = cursor_create_chat.fetchone()[0]

        # Add participants to the chat
        cursor_create_chat.execute("INSERT INTO Participants (chatID, userID) VALUES (%s, %s);", (chat_id, sender_id))
        cursor_create_chat.execute("INSERT INTO Participants (chatID, userID) VALUES (%s, %s);", (chat_id, receiver_id))

        # Commit the transaction
        get_db().commit()

        # Return success
        return return_statement(f"Chat created successfully!", "", 200)

    except mysql.connector.Error as e:
        # Rollback the transaction in case of error
        get_db().rollback()
        return return_statement("", str(e), 500)
    except Exception as e:
        get_db().rollback()
        return return_statement("", str(e), 500)
    finally:
        cursor_create_chat.close()

@app.route("/receive-message", methods=["POST", "GET"])
def receive_message():
    """
    Stores a message sent from one user to another.
    :return: Success or error message.
    """
    client = request.get_json()
    username = client.get("username", "").lower()
    receiver = client.get("receiver", "").lower()
    user_key = client.get("user_key", "")
    message = client.get("message", "")

    if not verif_user(username, user_key):
        return return_statement("", "Unable to verify user!", 400)

    cursor = get_db().cursor()
    try:
        # Get chat ID
        cursor.execute("""
        SELECT chatID FROM participants
        WHERE userID IN (
            SELECT userID FROM users WHERE username = %s
        )
        AND chatID IN (
            SELECT chatID FROM participants
            WHERE userID = (SELECT userID FROM users WHERE username = %s)
        )
        """, (username, receiver))
        chat_id = cursor.fetchone()

        if not chat_id:
            return return_statement("", "No chat found between users!", 400)

        # Insert message
        cursor.execute("""
        INSERT INTO messages (chatID, userID, message) VALUES (%s, (SELECT userID FROM users WHERE username = %s), %s)
        """, (chat_id[0], username, message))
        get_db().commit()
        return return_statement("Message sent successfully!")
    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor.close()

if __name__ == "__main__":
    print("server started")
    serve(app, host='0.0.0.0', port=5000)