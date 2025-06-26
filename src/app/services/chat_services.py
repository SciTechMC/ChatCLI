from flask import request
from app.services.base_services import verif_user, return_statement
from app.database.db_helper import fetch_records, insert_record

def fetch_chats():
    """
    Fetches chat participants for a user.
    """
    client = request.get_json()
    username = client.get("username", "").lower()
    session_token = client.get("session_token")

    # Verify the session token instead of user_key
    if not verif_user(username, session_token):
        return return_statement("", "Unable to verify user!", 400)

    try:
        # Lookup the user's ID
        users = fetch_records(
            table="users",
            where_clause="LOWER(username) = %s",
            params=(username,),
            fetch_all=True
        )
        if not users:
            return return_statement("", "User not found!", 404)
        user_id = users[0]["userID"]

        # Find all chatIDs this user participates in
        parts = fetch_records(
            table="participants",
            where_clause="userID = %s",
            params=(user_id,),
            fetch_all=True
        )
        chat_ids = [r["chatID"] for r in parts]
        if not chat_ids:
            return return_statement([], "", 200)

        # Find all participants in those chats, excluding the user
        fmt = ",".join(["%s"] * len(chat_ids))
        others = fetch_records(
            table="participants",
            where_clause=f"chatID IN ({fmt}) AND userID != %s",
            params=(*chat_ids, user_id),
            fetch_all=True
        )
        other_user_ids = list({r["userID"] for r in others})
        if not other_user_ids:
            return return_statement([], "", 200)

        # Get usernames for those userIDs
        fmt = ",".join(["%s"] * len(other_user_ids))
        rows = fetch_records(
            table="users",
            where_clause=f"userID IN ({fmt})",
            params=tuple(other_user_ids),
            fetch_all=True
        )
        chats = [r["username"] for r in rows]
        return return_statement(chats)

    except Exception as e:
        return return_statement("", str(e), 500)


def create_chat():
    """
    Creates a new chat between two users.
    """
    client = request.get_json()
    username = client.get("username", "").lower()
    receiver = client.get("receiver", "").lower()
    session_token = client.get("session_token")

    if not username or not receiver:
        return return_statement("", "Some statements are empty", 404)

    # Verify the session token
    if not verif_user(username, session_token):
        return return_statement("", "Unable to verify user!", 400)

    try:
        # Get user IDs for participants
        send = fetch_records(
            table="users",
            where_clause="LOWER(username) = %s",
            params=(username,),
            fetch_all=True
        )
        rec = fetch_records(
            table="users",
            where_clause="LOWER(username) = %s",
            params=(receiver,),
            fetch_all=True
        )
        if not send or not rec:
            return return_statement("", "Sender or receiver not found!", 400)
        sender_id = send[0]["userID"]
        receiver_id = rec[0]["userID"]

        # Create a new chat (no data fields)
        chat_id = insert_record("chats", {})

        # Add participants
        insert_record("participants", {"chatID": chat_id, "userID": sender_id})
        insert_record("participants", {"chatID": chat_id, "userID": receiver_id})

        return return_statement("Chat created successfully!", "", 200)

    except Exception as e:
        return return_statement("", str(e), 500)


def receive_message():
    """
    Stores a message sent from one user to another.
    """
    client = request.get_json()
    username = client.get("username", "").lower()
    receiver = client.get("receiver", "").lower()
    session_token = client.get("session_token")
    message = client.get("message", "")

    # Verify the session token
    if not verif_user(username, session_token):
        return return_statement("", "Unable to verify user!", 400)

    try:
        # Resolve sender ID
        user_rows = fetch_records(
            table="users",
            where_clause="LOWER(username) = %s",
            params=(username,),
            fetch_all=True
        )
        if not user_rows:
            return return_statement("", "Sender not found!", 404)
        sender_id = user_rows[0]["userID"]

        # Find the chat between the two users
        parts = fetch_records(
            table="participants",
            where_clause=(
                "userID = %s AND chatID IN ("
                "SELECT chatID FROM participants WHERE userID = ("
                "SELECT userID FROM users WHERE LOWER(username) = %s"
                ")"
                ")"
            ),
            params=(sender_id, receiver),
            fetch_all=True
        )
        if not parts:
            return return_statement("", "No chat found between users!", 400)
        chat_id = parts[0]["chatID"]

        if len(message) > 1000:
            return return_statement("", f"Message is too long! ({len(message)} chars/1000)", 400)

        # Insert the message
        insert_record("messages", {
            "chatID": chat_id,
            "userID": sender_id,
            "message": message
        })

        return return_statement("Message sent successfully!")

    except Exception as e:
        return return_statement("", str(e), 500)
    
def get_messages():
    """
    Retrieve the most recent messages from a chat.

    JSON body:
      - username       (str)
      - session_token  (str)
      - chatID         (int)
      - limit          (int, optional, defaults to 50, max 200)
    """
    data = request.get_json() or {}
    username      = data.get("username", "").lower()
    session_token = data.get("session_token")
    chat_id       = data.get("chatID")
    limit         = data.get("limit", 50)

    # Basic validation
    if not username or not session_token or not chat_id:
        return return_statement("", "username, session_token and chatID are required", 400)

    try:
        limit = int(limit)
    except (ValueError, TypeError):
        return return_statement("", "limit must be an integer", 400)

    # Enforce sensible bounds
    if limit < 1 or limit > 200:
        return return_statement("", "limit must be between 1 and 200", 400)

    # 1) Verify credentials
    if not verif_user(username, session_token):
        return return_statement("", "Unable to verify user!", 401)

    # 2) Check participation
    participants = fetch_records(
        table="participants",
        where_clause="chatID = %s AND userID = (SELECT userID FROM users WHERE LOWER(username) = %s)",
        params=(chat_id, username),
        fetch_all=True
    )
    if not participants:
        return return_statement("", "Chat not found or access denied", 404)

    # 3) Fetch messages
    #    We pull the latest N, then reverse so oldest→newest in the response
    rows = fetch_records(
        table="messages",
        where_clause="chatID = %s",
        params=(chat_id,),
        order_by="timestamp DESC",
        limit=limit,
        fetch_all=True
    )
    # reverse to chronological order
    messages = [
        {
            "messageID": r["messageID"],
            "userID":    r["userID"],
            "message":   r["message"],
            "timestamp": r["timestamp"].isoformat()
        }
        for r in reversed(rows)
    ]

    return return_statement(messages, "", 200)