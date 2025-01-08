import asyncio
import aiomysql
import random
import string
from flask import Flask, request, jsonify, g
import re
import db_envs

app = Flask(__name__)

# ---------------------------- DATABASE UTILITIES ----------------------------

async def get_db():
    """
    :return: An aiomysql database connection stored in Flask's 'g' object.
    """
    if 'db' not in g:
        env = db_envs.dev()  # Fetch database credentials
        g.db = await aiomysql.connect(
            host="localhost",
            user=env["user"],
            password=env["password"],
            db=env["db"],
        )
    return g.db

@app.teardown_appcontext
async def close_db(exception):
    """
    Ensures the database connection is closed after each request.
    :param exception: Any exception raised during the request.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

# ---------------------------- UTILITY FUNCTIONS ----------------------------

async def verif_user(username, user_key):
    """
    Verifies if the user and key match.
    """
    conn = await get_db()
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        await cursor.execute("SELECT user_key FROM Users WHERE username = %s", (username,))
        user = await cursor.fetchone()
        return user and user["user_key"] == user_key

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
async def verify_connection():
    """
    Test route to verify server is reachable.
    """
    return return_statement(response="Hello World!")

@app.route("/register", methods=["POST"])
async def register():
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
    if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
        return return_statement("", "Invalid email address", 400)
    if len(password) < 8 or password not in (string.ascii_uppercase, string.ascii_lowercase, string.punctuation):
        return return_statement("", "Your password must contain at least 8 characters, including an uppercase letter, a lowercase letter, a number, and a special character!", 400)

    conn = await get_db()
    async with conn.cursor() as cursor:
        try:
            # Check if the user already exists
            await cursor.execute("SELECT 1 FROM Users WHERE username = %s", (username,))
            if await cursor.fetchone():
                return return_statement("", f"User '{username}' already exists", 400)

            # Insert the new user
            await cursor.execute(
                "INSERT INTO Users (username, password, email) VALUES (%s, %s, %s)",
                (username, password, email)
            )
            await conn.commit()
            return return_statement(f"User '{username}' registered successfully!")
        except aiomysql.Error as e:
            return return_statement("", str(e), 500)

@app.route("/login", methods=["POST"])
async def login():
    """
    Logs in a user by validating credentials and generating a session key.
    """
    client = request.get_json()
    username = client.get("username").lower()
    password = client.get("password")

    conn = await get_db()
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        try:
            await cursor.execute("SELECT userID, password FROM Users WHERE username = %s", (username,))
            user = await cursor.fetchone()

            if not user:
                return return_statement("", "Username not found!", 404)
            if user["password"] != password:
                return return_statement("", "Invalid password", 400)

            # Generate a session key
            user_key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=24))
            await cursor.execute("UPDATE Users SET user_key = %s WHERE userID = %s", (user_key, user["userID"]))
            await conn.commit()
            return return_statement("Login Successful!", additional=["user_key", user_key])
        except aiomysql.Error as e:
            return return_statement("", str(e), 500)

@app.route("/fetch-chats", methods=["POST"])
async def fetch_chats():
    """
    Fetches chat participants for a user.
    """
    client = request.get_json()
    username = client.get("username").lower()
    user_key = client.get("user_key")

    if not await verif_user(username, user_key):
        return return_statement("", "Unable to verify user!", 400)

    conn = await get_db()
    async with conn.cursor() as cursor:
        try:
            await cursor.execute("""
            SELECT DISTINCT u.username
            FROM Users u
            JOIN Participants p ON u.userID = p.userID
            WHERE p.chatID IN (
                SELECT chatID FROM Participants
                WHERE userID = (SELECT userID FROM Users WHERE username = %s)
            ) AND u.userID != (SELECT userID FROM Users WHERE username = %s)
            """, (username, username))
            chats = [row[0] for row in await cursor.fetchall()]
            return return_statement(chats)
        except aiomysql.Error as e:
            return return_statement("", str(e), 500)

@app.route("/create-chat", methods=["POST"])
async def create_chat():
    """
    Creates a new chat between two users.
    """
    client = request.get_json()
    username = client.get("username").lower()
    receiver = client.get("receiver").lower()
    user_key = client.get("user_key")

    if not username or not receiver:
        return return_statement("", "Some statements are empty", 404)

    if not await verif_user(username, user_key):
        return return_statement("", "Unable to verify user!", 400)

    conn = await get_db()
    async with conn.cursor() as cursor:
        try:
            await conn.begin()

            # Get user IDs for participants
            await cursor.execute("SELECT userID FROM Users WHERE LOWER(username) = %s;", (username,))
            sender_id = await cursor.fetchone()

            await cursor.execute("SELECT userID FROM Users WHERE LOWER(username) = %s;", (receiver,))
            receiver_id = await cursor.fetchone()

            if not sender_id or not receiver_id:
                return return_statement("", "Sender or receiver not found!", 400)

            sender_id, receiver_id = sender_id[0], receiver_id[0]

            # Create a new chat
            await cursor.execute("INSERT INTO Chats () VALUES ();")
            await cursor.execute("SELECT LAST_INSERT_ID();")
            chat_id = (await cursor.fetchone())[0]

            # Add participants
            await cursor.execute("INSERT INTO Participants (chatID, userID) VALUES (%s, %s);", (chat_id, sender_id))
            await cursor.execute("INSERT INTO Participants (chatID, userID) VALUES (%s, %s);", (chat_id, receiver_id))

            await conn.commit()
            return return_statement(f"Chat created successfully!", "", 200)
        except aiomysql.Error as e:
            await conn.rollback()
            return return_statement("", str(e), 500)

@app.route("/receive-message", methods=["POST"])
async def receive_message():
    """
    Stores a message sent from one user to another.
    """
    client = request.get_json()
    username = client.get("username").lower()
    receiver = client.get("receiver").lower()
    user_key = client.get("user_key")
    message = client.get("message")

    if not await verif_user(username, user_key):
        return return_statement("", "Unable to verify user!", 400)

    conn = await get_db()
    async with conn.cursor() as cursor:
        try:
            await cursor.execute("""
            SELECT chatID FROM Participants
            WHERE userID IN (SELECT userID FROM Users WHERE username = %s)
            AND chatID IN (
                SELECT chatID FROM Participants
                WHERE userID = (SELECT userID FROM Users WHERE username = %s)
            )
            """, (username, receiver,))
            chat_id = await cursor.fetchone()

            if not chat_id:
                return return_statement("", "No chat found between users!", 400)

            chat_id = chat_id[0]

            # Insert message
            await cursor.execute("""
            INSERT INTO Messages (chatID, userID, message)
            VALUES (%s, (SELECT userID FROM Users WHERE username = %s), %s)
            """, (chat_id, username, message,))
            await conn.commit()
            return return_statement("Message sent successfully!")
        except aiomysql.Error as e:
            return return_statement("", str(e), 500)

# ---------------------------- RUN SERVER ----------------------------

if __name__ == "__main__":
    app.run(debug=True)
