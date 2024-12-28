import mysql.connector
import random
import string

from flask import Flask, request, jsonify, g

app = Flask(__name__)

# DATABASE-------------
def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host="localhost",
            user="chatcli_access",
            password="test1234",
            database="ChatCLI"
        )
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()
    if exception is not None:
        print(f"An exception occurred: {exception}")

# DATABASE--------------

def verif_user(username, user_key):
    """
    :param username: The client's username
    :param user_key: The key that the client has sent to the server
    :return: True or False depending on the user validity
    """
    cursor = get_db().cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user[5] == user_key:  # Adjusted from 'key' to 'user_key'
            return True
        return False
    except mysql.connector.Error as e:
        print(e)
    finally:
        cursor.close()

def return_statement(response = None, error: str = "", status_code: int = 200, additional=None):
    """
    :param response: The data to be sent back to the client.
    :param error: The error message.
    :param status_code: Check 'http status codes.txt' for more info.
    :param additional: List including additional info structured : ["name of dict variable" : "info"]

    :return: A JSON response with response and error, and the HTTP status code.
    """
    return jsonify({
        "response": response,
        "error": error,
        **(dict([additional]) if additional else {})
    }), status_code


@app.route("/verify-connection", methods=["GET"])
def verify_connection():
    return return_statement(response="Hello World!")


@app.route("/register", methods=["POST"])
def register():
    client = request.get_json()  # Corrected JSON parsing
    username = client.get("username")
    password = client.get("password")
    email = client.get("email")

    if not username or not password:
        return return_statement("", "Username and password are required", 400)

    cursor_register = get_db().cursor()

    try:
        # Check if user already exists
        cursor_register.execute("SELECT * FROM Users WHERE username = %s;", (username,))
        if cursor_register.fetchone():
            return return_statement("", f"User '{username}' already exists", 400)

        # Insert new user
        cursor_register.execute("""
        INSERT INTO Users (username, password, email)
        VALUES (%s, %s, %s);
        """, (username, password, email,))
        get_db().commit()
        return return_statement(f"User '{username}' registered successfully", "", 200)
    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor_register.close()

@app.route("/login", methods=["POST"])
def login():
    client = request.get_json()
    username = client.get("username")
    password = client.get("password")

    cursor_login = get_db().cursor()

    try:
        cursor_login.execute("Select * from users WHERE username=%s", (username,))
        user = cursor_login.fetchone()
        user_id = user[0]
        if user:
            if user[1] == username and user[2] == password:
                user_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(24))
                cursor_login.execute("""
                UPDATE users
                SET user_key = %s
                WHERE userID = %s;
                """, (user_key, user_id,))
                get_db().commit()
                return return_statement("Login Successful!", additional=["user_key", user_key])
            elif user[2] != password:
                return return_statement("", "Password does not match!",400)

    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor_login.close()

@app.route("/fetch-chats")
def fetch_chats():
    client = request.get_json()
    username = client.get("username")
    user_key = client.get("user_key")  # Adjusted from 'key' to 'user_key'

    cursor_fetch_chats = get_db().cursor()

    # Check client validity
    try:
        if not verif_user(username, user_key):  # Adjusted to use 'user_key'
            return return_statement("", "Unable to verify user!", 400)

        # chatgpt
        cursor_fetch_chats.execute("""
        SELECT DISTINCT u.username
        FROM Users u
        JOIN Participants p ON u.userID = p.userID
        WHERE p.chatID IN (
            SELECT chatID
            FROM Participants
            WHERE userID = (SELECT userID FROM Users WHERE username = %s)
        ) AND u.userID != (SELECT userID FROM Users WHERE username = %s);
        """, (username, username))
        client_chats = [row[0] for row in cursor_fetch_chats.fetchall()]
        return return_statement(client_chats)
    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor_fetch_chats.close()

@app.route("/create-chat", methods=["POST"])
def create_chat():
    client = request.get_json()
    username = client.get("username")
    receiver = client.get("receiver")
    user_key = client.get("user_key")  # Adjusted from 'key' to 'user_key'

    if not verif_user(username, user_key):  # Adjusted to use 'user_key'
        return return_statement("", "Unable to verify user!", 400)

    cursor_create_chat = get_db().cursor()

    try:
        # Step 1: Create a new chat
        cursor_create_chat.execute("INSERT INTO Chats () VALUES ();")
        get_db().commit()  # Commit to ensure LAST_INSERT_ID() is available

        # Step 2: Retrieve the new chatID
        cursor_create_chat.execute("SELECT LAST_INSERT_ID();")
        chat_id = cursor_create_chat.fetchone()[0]

        # Step 3: Get user IDs for participants
        cursor_create_chat.execute("SELECT userID FROM Users WHERE username = %s;", (username,))
        user_id = cursor_create_chat.fetchone()[0]

        cursor_create_chat.execute("SELECT userID FROM Users WHERE username = %s;", (receiver,))
        receiver_id = cursor_create_chat.fetchone()

        if not receiver_id:
            return return_statement("", "Receiver does not exist", 400)
        receiver_id = receiver_id[0]

        # Step 4: Add participants to the chat
        cursor_create_chat.execute("INSERT INTO ChatParticipants (chatID, userID) VALUES (%s, %s);", (chat_id, user_id))
        cursor_create_chat.execute("INSERT INTO ChatParticipants (chatID, userID) VALUES (%s, %s);", (chat_id, receiver_id))
        get_db().commit()

        # Step 5: Return success
        return return_statement(f"Chat created successfully!", "", 200)

    except mysql.connector.Error as e:
        get_db().rollback()  # Rollback in case of error
        return return_statement("", str(e), 500)
    finally:
        cursor_create_chat.close()

@app.route("/receive-message")
def receive_message():
    client = request.get_json()
    username = client.get("username")
    receiver = client.get("receiver")
    user_key = client.get("user_key")  # Adjusted from 'key' to 'user_key'
    message = client.get("message")

    # Verify user authentication
    if not verif_user(username, user_key):  # Adjusted to use 'user_key'
        return return_statement("", "Unable to verify user!", 400)

    cursor_receive = get_db().cursor()

    try:
        # Fetch user information for receiver and sender
        cursor_receive.execute("""SELECT * FROM Users WHERE username = %s;""", (receiver,))
        receiver_info = cursor_receive.fetchone()

        cursor_receive.execute("""SELECT * FROM Users WHERE username = %s;""", (username,))
        sender_info = cursor_receive.fetchone()

        # Check if both the sender and receiver exist
        if not receiver_info or not sender_info:
            return return_statement("", "Sender or receiver not found!", 400)

        # Get the chatID for the participants (sender and receiver)
        cursor_receive.execute("SELECT chatID FROM Participants WHERE userID IN (%s, %s);", (receiver_info[0], sender_info[0],))
        chat_id_results = cursor_receive.fetchall()

        if not chat_id_results:
            return return_statement("", "No chat found between the users!", 400)

        # Assuming only one chatID exists
        chat_id = chat_id_results[0][0]

        # Insert the message into the Messages table
        cursor_receive.execute("""
        INSERT INTO Messages (chatID, userID, message)
        VALUES (%s, %s, %s);
        """, (chat_id, sender_info[0], message,))
        get_db().commit()

        return return_statement("", "", 200)

    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor_receive.close()

if __name__ == "__main__":
    # Debug mode should only be enabled in development
    app.run(debug=True)  # Disable debug for production