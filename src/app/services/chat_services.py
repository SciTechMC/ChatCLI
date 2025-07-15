from flask import request, current_app
from app.services.base_services import authenticate_token, return_statement
from app.database.db_helper import (
    transactional,
    insert_record,
    fetch_records,
    get_db,
    update_records
)
import mysql.connector
import logging
import os

tmp_logger = logging.getLogger(__name__)

def fetch_chats():
    """
    POST JSON: { session_token }
    Returns: { response: [ { chatID, name, type }, … ], status }
    """
    client = request.get_json() or {}
    session_token = client.get("session_token")

    username = authenticate_token(session_token)
    if not username:
        return return_statement([], "Unable to verify user!", 401)

    # Get userID
    rows = fetch_records(
        table="users",
        where_clause="LOWER(username) = %s",
        params=(username.lower(),),
        fetch_all=True
    )
    if not rows:
        return return_statement([], "User not found", 404)
    user_id = rows[0]["userID"]

    # Get all chatIDs
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT chatID FROM participants WHERE userID = %s AND archived = 0",
        (user_id,)
    )

    chat_ids = [r[0] for r in cursor.fetchall()]
    if not chat_ids:
        return return_statement([], "", 200)

    # Fetch chat metadata (type + group_name)
    fmt = ",".join(["%s"] * len(chat_ids))
    chats = fetch_records(
        table="chats",
        where_clause=f"chatID IN ({fmt})",
        params=tuple(chat_ids),
        fetch_all=True
    )

    # Build maps
    group_map = {c["chatID"]: c["group_name"] for c in chats if c["type"] == "group"}
    private_ids = [c["chatID"] for c in chats if c["type"] == "private"]

    # For private chats: find the other user
    chat_to_user = {}
    id_to_name = {}
    if private_ids:
        fmt2 = ",".join(["%s"] * len(private_ids))
        others = fetch_records(
            table="participants",
            where_clause=f"chatID IN ({fmt2}) AND userID != %s",
            params=(*private_ids, user_id),
            fetch_all=True
        )
        chat_to_user = {r["chatID"]: r["userID"] for r in others}

        # Resolve their usernames
        user_ids = list(chat_to_user.values())
        fmt3 = ",".join(["%s"] * len(user_ids))
        user_rows = fetch_records(
            table="users",
            where_clause=f"userID IN ({fmt3})",
            params=tuple(user_ids),
            fetch_all=True
        )
        id_to_name = {r["userID"]: r["username"] for r in user_rows}

    # Build the response array, now including type
    response = []
    for cid in chat_ids:
        if cid in group_map:
            response.append({
                "chatID": cid,
                "name": group_map[cid],
                "type": "group"
            })
        else:
            const_peer = chat_to_user.get(cid)
            response.append({
                "chatID": cid,
                "name": id_to_name.get(const_peer, "Unknown"),
                "type": "private"
            })
    return return_statement(response, "", 200)

def get_messages():
    """
    Retrieve the most recent messages from a chat.

    JSON body:
      - username (str)
      - session_token (str)
      - chatID (int)
      - limit (int, optional, defaults to 50, max 200)
    """
    data = request.get_json() or {}
    username = data.get("username", "").lower()
    session_token = data.get("session_token")
    chat_id = data.get("chatID")
    limit = data.get("limit", 50)

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
        fmt = ",".join(["%s"] * len(user_ids))
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
            "userID": r["userID"],
            "username": id_to_username.get(r["userID"], "unknown"),
            "message": r["message"],
            "timestamp": r["timestamp"].isoformat()
        }
        for r in reversed(rows)
    ]

    return return_statement(messages, "", 200)

def archive_chat():
    """
    Archives a chat for the user by setting archived=1.
    Other participants still see it.
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

    # Get the user's ID
    user_rows = fetch_records(
        table="users",
        where_clause="LOWER(username) = %s",
        params=(username.lower(),),
        fetch_all=True
    )
    if not user_rows:
        return return_statement("", "User not found!", 404)
    user_id = user_rows[0]["userID"]

    conn = get_db()
    cursor = conn.cursor()
    try:
        # Set archived=1 for this user+chat
        cursor.execute(
            "UPDATE participants SET archived = 1 WHERE chatID = %s AND userID = %s",
            (chat_id, user_id)
        )
        conn.commit()
        return return_statement("", "Chat archived", 200)
    except Exception as e:
        current_app.logger.exception("Error archiving chat")
        return return_statement("", "Could not archive chat", 500)

def get_members():
    """
    POST JSON:
      - session_token (str)
      - chatID (int)
    Returns: { response: [username1, username2, ...], status }
    """
    client = request.get_json() or {}
    tok = client.get("session_token")
    cid = client.get("chatID")
    user = authenticate_token(tok)
    if not user:
        return return_statement([], "Invalid session token", 401)

    # Validate group
    grp = fetch_records("chats", "chatID=%s AND type='group'", (cid,), fetch_all=True)
    if not grp:
        return return_statement([], "Group not found", 404)

    # Get participants
    parts = fetch_records(
        table="participants",
        where_clause="chatID=%s",
        params=(cid,),
        fetch_all=True
    )
    ids = [p["userID"] for p in parts]

    # Resolve usernames
    fmt = ",".join(["%s"] * len(ids))
    users = fetch_records(
        table="users",
        where_clause=f"userID IN ({fmt})",
        params=tuple(ids),
        fetch_all=True
    )
    names = [u["username"] for u in users]
    return return_statement(names, "", 200)

@transactional
def add_participant():
    """
    POST JSON:
      - session_token (str)
      - chatID (int)
      - members (list[str])
    """
    client = request.get_json() or {}
    token = client.get("session_token")
    chat_id = client.get("chatID")
    new_us = client.get("members", [])

    user = authenticate_token(token)
    if not user:
        return return_statement([], "Invalid session token", 401)

    # Verify group
    chat = fetch_records("chats", "chatID=%s AND type='group'", (chat_id,), fetch_all=True)
    if not chat:
        return return_statement([], "Group not found", 404)

    # Lookup userIDs
    ph = ",".join(["%s"] * len(new_us))
    rows = fetch_records("users", f"LOWER(username) IN ({ph})", tuple(u.lower() for u in new_us), fetch_all=True)
    if len(rows) != len(new_us):
        return return_statement([], "One or more users not found", 404)
    ids = [r["userID"] for r in rows]

    # Insert, ignore duplicates
    conn = get_db()
    cur = conn.cursor()
    for uid in set(ids):
        try:
            cur.execute("INSERT INTO participants (chatID,userID) VALUES (%s,%s)", (chat_id, uid))
        except:
            pass
    conn.commit()
    return return_statement({"chatID": chat_id}, "Members added", 200)

@transactional
def remove_participant():
    """
    POST JSON:
      - session_token (str)
      - chatID (int)
      - members (list[str])
    """
    client = request.get_json() or {}
    token = client.get("session_token")
    chat_id = client.get("chatID")
    rem_us = client.get("members", [])

    user = authenticate_token(token)
    if not user:
        return return_statement([], "Invalid session token", 401)

    # Verify group
    chat = fetch_records("chats", "chatID=%s AND type='group'", (chat_id,), fetch_all=True)
    if not chat:
        return return_statement([], "Group not found", 404)

    # Lookup userIDs
    ph = ",".join(["%s"] * len(rem_us))
    rows = fetch_records("users", f"LOWER(username) IN ({ph})", tuple(u.lower() for u in rem_us), fetch_all=True)
    ids = [r["userID"] for r in rows]

    # Delete them
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM participants WHERE chatID=%s AND userID IN ({ph})", (chat_id, *ids))
    conn.commit()

    # If <2 left, just remove the last participant — leave chat & messages intact
    cur.execute("SELECT COUNT(*) FROM participants WHERE chatID=%s", (chat_id,))
    if cur.fetchone()[0] < 2:
        # delete any remaining participant row(s)
        cur.execute("DELETE FROM participants WHERE chatID=%s", (chat_id,))
        conn.commit()
        return return_statement({"chatID": chat_id}, "Participant removed, chat retained", 200)

    return return_statement({"chatID": chat_id}, "Members removed", 200)

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
        if os.getenv("FLASK_ENV") == "development":
            print(f"Inserted sender {sender_id} into chat {chat_id}")
        cursor.execute(
            "INSERT INTO participants (chatID, userID) VALUES (%s, %s)",
            (chat_id, receiver_id),
        )
        if os.getenv("FLASK_ENV") == "development":
            print(f"Inserted receiver {receiver_id} into chat {chat_id}")
    except mysql.connector.IntegrityError as e:
        # If duplicate, rollback and raise a user-friendly error
        conn.rollback()
        raise Exception("Participant already exists in this chat") from e
    except mysql.connector.Error as e:
        # Handle other MySQL errors
        conn.rollback()
        if os.getenv("FLASK_ENV") == "development":
            print(f"Database error: {str(e)}")
        else:
            tmp_logger.error("Database error: %s", str(e))
        raise Exception(f"Database error: {str(e)}") from e

def create_chat():
    """
    Endpoint: verifies token, resolves IDs, checks duplicates,
    then calls the transactional helper above.
    """
    client = request.get_json() or {}
    session_tok = client.get("session_token")
    receiver = (client.get("receiver") or "").lower()

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

        sender_id = send[0]["userID"]
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
        return return_statement("", "An internal server error occurred", 500)

@transactional
def _create_group_logic(owner_id: int, group_name: str, member_ids: list[int]) -> int:
    conn = get_db()
    cursor = conn.cursor()

    # 1) insert the group chat
    cursor.execute(
        "INSERT INTO chats (type, group_name) VALUES ('group', %s)",
        (group_name,)
    )
    chat_id = cursor.lastrowid

    # 2) insert participants (owner + each member)
    all_ids = {owner_id, *member_ids}
    for uid in all_ids:
        cursor.execute(
            "INSERT INTO participants (chatID, userID) VALUES (%s, %s)",
            (chat_id, uid)
        )

    return chat_id

def create_group():
    """
    JSON body:
      - session_token (str)
      - name (str): the group’s name
      - members (list[str]): usernames to include
    """
    client = request.get_json() or {}
    tok = client.get("session_token")
    name = client.get("name", "").strip()
    mems = client.get("members", [])

    if not tok or not name or not isinstance(mems, list) or not mems:
        return return_statement("", "token, name and members list are required", 400)

    username = authenticate_token(tok)
    if not username:
        return return_statement("", "Invalid session token", 401)

    # Lookup owner
    send = fetch_records("users", "LOWER(username)=%s", (username,), fetch_all=True)
    owner_id = send[0]["userID"]

    # Lookup member IDs
    placeholders = ",".join(["%s"] * len(mems))
    rows = fetch_records(
        table="users",
        where_clause=f"LOWER(username) IN ({placeholders})",
        params=tuple(u.lower() for u in mems),
        fetch_all=True
    )
    if len(rows) != len(mems):
        return return_statement("", "One or more members not found", 404)
    member_ids = [r["userID"] for r in rows]

    try:
        chat_id = _create_group_logic(owner_id, name, member_ids)
        return return_statement({"chatID": chat_id}, "", 201)
    except Exception as e:
        current_app.logger.exception("Error creating group")
        return return_statement("", "Could not create group", 500)
