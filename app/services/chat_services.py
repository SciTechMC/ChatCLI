from flask import request
from app.services.base_services import verif_user,return_statement,get_db
import mysql.connector

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

        if len(message) > 1000:
            return return_statement("",f"Message is to long! ({len(message)} chars/1000)", 400)

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