from flask import request, current_app
from app.services.base_services import authenticate_token, return_statement
from app.database.db_helper import transactional, insert_record, fetch_records, get_db, update_records
import mysql.connector

def fetch_chats():
    """
    Fetches chat participants for a user.
    Returns: {
      "response": [
        { "chatID": ..., "name": ... },
        ...
      ],
      "status": "ok"
    }
    """
    client = request.get_json() or {}
    session_token = client.get("session_token")

    # Verify the session token
    username = authenticate_token(session_token)
    if not username:
        return {"response": [], "status": "Unable to verify user!"}

    try:
        # Lookup the user's ID
        users = fetch_records(
            table="users",
            where_clause="LOWER(username) = %s",
            params=(username,),
            fetch_all=True
        )
        if not users:
            return {"response": [], "status": "User not found!"}
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
            return {"response": [], "status": "ok"}

        # Find all participants in those chats, excluding the user
        fmt = ",".join(["%s"] * len(chat_ids))
        others = fetch_records(
            table="participants",
            where_clause=f"chatID IN ({fmt}) AND userID != %s",
            params=(*chat_ids, user_id),
            fetch_all=True
        )
        chat_to_user = {r["chatID"]: r["userID"] for r in others}
        if not chat_to_user:
            return {"response": [], "status": "ok"}

        # Get usernames for those userIDs
        other_user_ids = list(set(chat_to_user.values()))
        fmt = ",".join(["%s"] * len(other_user_ids))
        rows = fetch_records(
            table="users",
            where_clause=f"userID IN ({fmt})",
            params=tuple(other_user_ids),
            fetch_all=True
        )
        id_to_name = {r["userID"]: r["username"] for r in rows}

        # Build response
        response = [
            {"chatID": cid, "name": id_to_name[uid]}
            for cid, uid in chat_to_user.items()
        ]
        return {"response": response, "status": "ok"}

    except Exception as e:
        return {"response": [], "status": str(e)}


@transactional
def _create_chat_logic(sender_id: int, receiver_id: int) -> None:
    conn = get_db()
    cursor = conn.cursor()

    # 1) Check if chat already exists (atomic check)
    cursor.execute(
        """
        SELECT c.chatID
        FROM chats c
        JOIN participants p1 ON c.chatID = p1.chatID AND p1.userID = %s
        JOIN participants p2 ON c.chatID = p2.chatID AND p2.userID = %s
        WHERE c.type = 'private'
        """,
        (sender_id, receiver_id)
    )
    row = cursor.fetchone()
    if row:
        raise Exception("Chat already exists between these users!")

    # 2) create chat
    cursor.execute("INSERT INTO chats (type) VALUES ('private')")
    chat_id = cursor.lastrowid

    # 3) link participants
    try:
        cursor.execute(
            "INSERT INTO participants (chatID, userID) VALUES (%s, %s)",
            (chat_id, sender_id),
        )
        print(f"Inserted sender {sender_id} into chat {chat_id}")
        cursor.execute(
            "INSERT INTO participants (chatID, userID) VALUES (%s, %s)",
            (chat_id, receiver_id),
        )
        print(f"Inserted receiver {receiver_id} into chat {chat_id}")
    except mysql.connector.IntegrityError as e:
        # If duplicate, rollback and raise a user-friendly error
        conn.rollback()
        raise Exception("Participant already exists in this chat") from e
    except mysql.connector.Error as e:
        # Handle other MySQL errors
        conn.rollback()
        print(f"Database error: {str(e)}")
        raise Exception(f"Database error: {str(e)}") from e

def create_chat():
    """
    Endpoint: verifies token, resolves IDs, checks duplicates,
    then calls the transactional helper above.
    """
    client      = request.get_json() or {}
    session_tok = client.get("session_token")
    receiver    = (client.get("receiver") or "").lower()

    if not session_tok or not receiver:
        return return_statement("", "Session token and receiver are required", 400)

    # Verify the session token
    username = authenticate_token(session_tok)
    if not username:
        return return_statement("", "Unable to verify user!", 400)

    try:
        # Resolve sender and receiver IDs
        send = fetch_records(
            table="users",
            where_clause="LOWER(username) = %s",
            params=(username,),
            fetch_all=True,
        )
        rec = fetch_records(
            table="users",
            where_clause="LOWER(username) = %s",
            params=(receiver,),
            fetch_all=True,
        )
        if not send or not rec:
            return return_statement("", "Sender or receiver not found!", 400)

        sender_id   = send[0]["userID"]
        receiver_id = rec[0]["userID"]

        # Prevent duplicate chats
        existing = fetch_records(
            table="participants",
            where_clause=(
                "userID IN (%s, %s) "
                "AND chatID IN ("
                " SELECT chatID FROM participants WHERE userID IN (%s, %s) "
                " GROUP BY chatID HAVING COUNT(DISTINCT userID) = 2"
                ")"
            ),
            params=(sender_id, receiver_id, sender_id, receiver_id),
            fetch_all=True,
        )
        if existing:
            return return_statement("", "Chat already exists between these users!", 409)

        # Run the atomic logic
        _create_chat_logic(sender_id, receiver_id)
        return return_statement("Chat created successfully!", "", 200)

    except Exception as e:
        current_app.logger.exception("Error during chat creation")
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
    data          = request.get_json() or {}
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
    username = authenticate_token(session_token)
    if not username:
        return return_statement("", "Unable to verify user!", 401)

    # 2) Check participation
    participants = fetch_records(
        table="participants",
        where_clause="chatID = %s AND userID = (SELECT userID FROM users WHERE LOWER(username) = %s)",
        params=(chat_id, username),
        fetch_all=True,
    )
    if not participants:
        return return_statement("", "Chat not found or access denied", 404)

    # 3) Fetch messages
    rows = fetch_records(
        table="messages",
        where_clause="chatID = %s",
        params=(chat_id,),
        order_by="timestamp DESC",
        limit=limit,
        fetch_all=True,
    )

    # Map userIDs to usernames in bulk
    user_ids = list({r["userID"] for r in rows})
    id_to_username = {}
    if user_ids:
        fmt       = ",".join(["%s"] * len(user_ids))
        user_rows = fetch_records(
            table="users",
            where_clause=f"userID IN ({fmt})",
            params=tuple(user_ids),
            fetch_all=True,
        )
        id_to_username = {r["userID"]: r["username"] for r in user_rows}

    # Reverse to chronological order and include username
    messages = [
        {
            "messageID": r["messageID"],
            "userID":    r["userID"],
            "username":  id_to_username.get(r["userID"], "unknown"),
            "message":   r["message"],
            "timestamp": r["timestamp"].isoformat()
        }
        for r in reversed(rows)
    ]

    return return_statement(messages, "", 200)


def delete_chat():
    """
    Deletes a chat for the user by removing them as a participant.
    If no participants remain, the chat and its messages are deleted.
    """
    client = request.get_json() or {}
    session_token = client.get("session_token")
    chat_id = client.get("chatID")

    if not session_token or not chat_id:
        return return_statement("", "Session token and chatID are required", 400)

    # Verify the session token
    username = authenticate_token(session_token)
    if not username:
        return return_statement("", "Unable to verify user!", 401)

    try:
        # Get the user's ID
        user = fetch_records(
            table="users",
            where_clause="LOWER(username) = %s",
            params=(username,),
            fetch_all=True
        )
        if not user:
            return return_statement("", "User not found!", 404)
        user_id = user[0]["userID"]

        # Check if the user is a participant in the chat
        participant = fetch_records(
            table="participants",
            where_clause="chatID = %s AND userID = %s",
            params=(chat_id, user_id),
            fetch_all=True
        )
        if not participant:
            return return_statement("", "Chat not found or access denied", 404)

        # Remove the user from the participants table
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM participants WHERE chatID = %s AND userID = %s", (chat_id, user_id))
        conn.commit()

        # Check if there are any participants left in the chat
        remaining_participants = fetch_records(
            table="participants",
            where_clause="chatID = %s",
            params=(chat_id,),
            fetch_all=True
        )
        if not remaining_participants:
            # Delete the chat and its messages
            cursor.execute("DELETE FROM messages WHERE chatID = %s", (chat_id,))
            cursor.execute("DELETE FROM chats WHERE chatID = %s", (chat_id,))
            conn.commit()

        return return_statement("Chat deleted successfully!", "", 200)

    except Exception as e:
        current_app.logger.exception("Error during chat deletion")
        return return_statement("", str(e), 500)