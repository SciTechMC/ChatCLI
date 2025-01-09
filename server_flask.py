import random
import string
from flask import Flask, request, jsonify, g
import re
import mysql.connector
import bcrypt
import db_envs

#waitress-serve --host=0.0.0.0 --port=5000 --threads=4 --workers=9 --ssl-certfile=/certifs/cert.pem --ssl-keyfile=/certifs/privkey.pem server_flask:app

app = Flask(__name__)

# ---------------------------- DATABASE UTILITIES ----------------------------

def get_db():
    """
    :return: A MySQL database connection stored in Flask's 'g' object.
    """
    if 'db' not in g:
        env = db_envs.dev()  # Fetch database credentials
        g.db = mysql.connector.connect(
            host="localhost",
            user=env["user"],
            password=env["password"],
            database=env["db"]
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

def verif_user(username, session_token):
    """
    Verifies if the user and key match.
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
    SELECT session_token 
    FROM session_tokens 
    WHERE userID = (SELECT userID FROM Users WHERE username = %s)
    ORDER BY created_at DESC 
    LIMIT 1;
    """, (username,))
    user = cursor.fetchone()
    cursor.close()
    return user and user["session_token"] == session_token


def return_statement(response=None, error="", status_code=200, additional=None):
    """
    Standardized JSON response.
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
    # Handle POST request
    if request.method == "POST":
        # Ensure the JSON body exists
        client_data = request.get_json()
        if not client_data:
            return return_statement("", "Invalid request!", 400)

        version = client_data.get("version")
        if version == "post-alpha-dev-build":
            return return_statement(response="Hello World!")
        else:
            return return_statement("", "Incompatible client version!", 400)

    # Handle GET request
    elif request.method == "GET":
        return return_statement("", "Incompatible client version!", 400)

    # Fallback (should not be reached)
    return return_statement("", "Unsupported HTTP method!", 405)


@app.route("/register", methods=["POST"])
def register():
    """
    Registers a new user in the system.
    """
    client = request.get_json()
    username = client.get("username").lower()
    password = client.get("password")
    email = client.get("email")

    # Validate input fields
    if not username or not password:
        return return_statement("", "Username and password are required", 400)
    if any(char in r'"%\'()*+,/:;<=>?@[\]^{|}~` ' for char in username):
        return return_statement("", "Username includes bad characters", 400)
    if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA0-9-.]+$', email):
        return return_statement("", "Invalid email address", 400)
    if (
            len(password) < 8 or
            not any(char.isupper() for char in password) or
            not any(char.islower() for char in password) or
            not any(char.isdigit() for char in password) or
            not any(char in string.punctuation for char in password)
    ):
        return return_statement("",
                                "Your password must contain at least 8 characters, including an uppercase letter, a lowercase letter, a number, and a special character!",
                                400)

    password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    conn = get_db()
    cursor = conn.cursor()
    try:
        # Check if the user already exists
        cursor.execute("SELECT 1 FROM Users WHERE username = %s", (username,))
        if cursor.fetchone():
            return return_statement("", f"User '{username}' already exists", 400)

        # Insert the new user
        cursor.execute(
            "INSERT INTO Users (username, password, email) VALUES (%s, %s, %s)",
            (username, password, email)
        )
        conn.commit()
        return return_statement(f"User '{username}' registered successfully!")
    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor.close()


@app.route("/login", methods=["POST"])
def login():
    """
    Logs in a user by validating credentials and generating a session token.
    """
    client = request.get_json()
    username = client.get("username").lower()
    password = client.get("password")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch user data based on username
        cursor.execute("SELECT userID, password FROM Users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if not user:
            return return_statement("", "Username not found!", 404)
        if not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
            return return_statement("", "Invalid password", 400)

        # Generate a new session token
        session_token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=64))

        # Insert the session token into the session_tokens table
        cursor.execute("""
            INSERT INTO session_tokens (userID, session_token, ip_address, is_active) 
            VALUES (%s, %s, %s, TRUE)
        """, (user["userID"], session_token, request.remote_addr))
        conn.commit()

        return return_statement("Login Successful!", additional=["session_token", session_token])
    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor.close()


@app.route("/fetch-chats", methods=["POST"])
def fetch_chats():
    """
    Fetches chat participants for a user.
    """
    client = request.get_json()
    username = client.get("username").lower()
    session_token = client.get("session_token")

    # Verify the session token instead of user_key
    if not verif_user(username, session_token):
        return return_statement("", "Unable to verify user!", 400)

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT DISTINCT u.username
        FROM Users u
        JOIN Participants p ON u.userID = p.userID
        WHERE p.chatID IN (
            SELECT chatID FROM Participants
            WHERE userID = (SELECT userID FROM Users WHERE username = %s)
        ) AND u.userID != (SELECT userID FROM Users WHERE username = %s)
        """, (username, username))

        chats = [row[0] for row in cursor.fetchall()]
        return return_statement(chats)
    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor.close()

@app.route("/create-chat", methods=["POST"])
def create_chat():
    """
    Creates a new chat between two users.
    """
    client = request.get_json()
    username = client.get("username").lower()
    receiver = client.get("receiver").lower()
    session_token = client.get("session_token")

    if not username or not receiver:
        return return_statement("", "Some statements are empty", 404)

    # Verify the session token instead of user_key
    if not verif_user(username, session_token):
        return return_statement("", "Unable to verify user!", 400)

    conn = get_db()
    cursor = conn.cursor()
    try:
        # Get user IDs for participants
        cursor.execute("SELECT userID FROM Users WHERE LOWER(username) = %s;", (username,))
        sender_id = cursor.fetchone()

        cursor.execute("SELECT userID FROM Users WHERE LOWER(username) = %s;", (receiver,))
        receiver_id = cursor.fetchone()

        if not sender_id or not receiver_id:
            return return_statement("", "Sender or receiver not found!", 400)

        sender_id, receiver_id = sender_id[0], receiver_id[0]

        # Create a new chat
        cursor.execute("INSERT INTO Chats () VALUES ();")
        cursor.execute("SELECT LAST_INSERT_ID();")
        chat_id = cursor.fetchone()[0]

        # Add participants
        cursor.execute("INSERT INTO Participants (chatID, userID) VALUES (%s, %s);", (chat_id, sender_id))
        cursor.execute("INSERT INTO Participants (chatID, userID) VALUES (%s, %s);", (chat_id, receiver_id))

        conn.commit()
        return return_statement(f"Chat created successfully!", "", 200)
    except mysql.connector.Error as e:
        conn.rollback()
        return return_statement("", str(e), 500)
    finally:
        cursor.close()

@app.route("/receive-message", methods=["POST"])
def receive_message():
    """
    Stores a message sent from one user to another.
    """
    client = request.get_json()
    username = client.get("username").lower()
    receiver = client.get("receiver").lower()
    session_token = client.get("session_token")  # Changed to session_token
    message = client.get("message")

    # Verify user with session token instead of user_key
    if not verif_user(username, session_token):
        return return_statement("", "Unable to verify user!", 400)

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT chatID FROM Participants
        WHERE userID IN (SELECT userID FROM Users WHERE username = %s)
        AND chatID IN (
            SELECT chatID FROM Participants
            WHERE userID = (SELECT userID FROM Users WHERE username = %s)
        )
        """, (username, receiver,))
        chat_id = cursor.fetchone()

        if not chat_id:
            return return_statement("", "No chat found between users!", 400)

        chat_id = chat_id[0]

        # Insert message
        cursor.execute("""
        INSERT INTO Messages (chatID, userID, message)
        VALUES (%s, (SELECT userID FROM Users WHERE username = %s), %s)
        """, (chat_id, username, message,))
        conn.commit()
        return return_statement("Message sent successfully!")
    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor.close()

# ---------------------------- RUN SERVER ----------------------------

if __name__ == "__main__":
    cert_path = '/etc/letsencrypt/live/<your-domain>/cert.pem'
    key_path = '/etc/letsencrypt/live/<your-domain>/privkey.pem'

    app.run(host="0.0.0.0",debug=True, ssl_context=('./certifs/fullchain.pem', './certifs/privkey.pem'))
