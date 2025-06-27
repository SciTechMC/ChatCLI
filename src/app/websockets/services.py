# app/websockets/services.py

from fastapi import WebSocket, status
from app.services.base_services import verif_user
from app.database.db_helper import fetch_records, insert_record
from app.database.db_helper import get_db   # for DELETE in leave_chat
import logging
import bcrypt

# In-memory connection & subscription registries
active_connections: dict[str, WebSocket] = {}
chat_subscriptions: dict[int, set[WebSocket]] = {}

async def authenticate(websocket: WebSocket, msg: dict) -> str | None:
    """
    Token-only auth. Client must send:
      { "type":"auth", "token":"<plain-text session token>" }

    We look up the matching bcrypt hash in session_tokens,
    load the user’s username, register the WS, and return it.
    Otherwise we close immediately.
    """
    token = msg.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    # Find the session whose hash matches this token and is still valid
    sessions = fetch_records(
        table="session_tokens",
        where_clause="revoked = FALSE AND expires_at > CURRENT_TIMESTAMP()",
        fetch_all=True
    )

    matched = None
    for s in sessions:
        try:
            if bcrypt.checkpw(token.encode("utf-8"), s["session_token"].encode("utf-8")):
                matched = s
                break
        except ValueError:
            continue

    if not matched:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    # Lookup the username for that session’s userID
    users = fetch_records(
        table="users",
        where_clause="userID = %s",
        params=(matched["userID"],),
        fetch_all=True
    )
    if not users:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return None

    username = users[0]["username"]
    active_connections[username] = websocket
    return username

async def join_chat(username: str, chat_id: int) -> bool:
    """
    Adds the (username, chat_id) pair to the participants table
    and subscribes that user's WebSocket to future broadcasts.
    """
    # fetch userID
    users = fetch_records(
        table="users",
        where_clause="username = %s",
        params=(username,),
        fetch_all=True
    )
    if not users:
        return False
    user_id = users[0]["userID"]

    # insert into participants (ignore duplicates)
    try:
        insert_record("participants", {"chatID": chat_id, "userID": user_id})
    except Exception:
        # if it already exists, that's fine
        pass

    # subscribe
    ws = active_connections.get(username)
    if ws:
        chat_subscriptions.setdefault(chat_id, set()).add(ws)
    return True

async def leave_chat(username: str, chat_id: int) -> bool:
    """
    Removes the (username, chat_id) pair from participants 
    and unsubscribes that user's WebSocket.
    """
    # fetch userID
    users = fetch_records(
        table="users",
        where_clause="username = %s",
        params=(username,),
        fetch_all=True
    )
    if not users:
        return False
    user_id = users[0]["userID"]

    # delete from participants
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "DELETE FROM participants WHERE chatID = %s AND userID = %s",
            (chat_id, user_id)
        )
        db.commit()
    except Exception as e:
        logging.error(f"[leave_chat] delete error: {e}")
        db.rollback()
        return False

    # unsubscribe
    ws = active_connections.get(username)
    if ws and chat_id in chat_subscriptions:
        chat_subscriptions[chat_id].discard(ws)
    return True

async def post_msg(msg: dict) -> dict | None:
    """
    Inserts a new chat message into the DB and broadcasts it.
    Expects: { 'username': str, 'chatID': int, 'text': str }
    Returns the payload that was broadcast.
    """
    username = msg.get("username", "").lower()
    chat_id  = msg.get("chatID")
    text     = msg.get("text", "")

    # basic validation
    if not (username and chat_id and text):
        return None

    # get userID
    users = fetch_records(
        table="users",
        where_clause="username = %s",
        params=(username,),
        fetch_all=True
    )
    if not users:
        return None
    user_id = users[0]["userID"]

    # insert into messages
    message_id = insert_record(
        "messages",
        {"chatID": chat_id, "userID": user_id, "message": text}
    )

    # re-fetch the row to get timestamp etc.
    rows = fetch_records(
        table="messages",
        where_clause="messageID = %s",
        params=(message_id,),
        fetch_all=True
    )
    if not rows:
        return None
    row = rows[0]

    payload = {
        "type":      "new_message",
        "messageID": row["messageID"],
        "chatID":    row["chatID"],
        "userID":    row["userID"],
        "message":   row["message"],
        "timestamp": row["timestamp"].isoformat()
    }

    # broadcast to everyone in the chat
    await broadcast_msg(chat_id, payload)
    return payload

async def broadcast_msg(chat_id: int, payload: dict):
    """
    Sends `payload` (a dict) as JSON to every WebSocket
    subscribed to `chat_id`. Silently skips closed connections.
    """
    subscribers = chat_subscriptions.get(chat_id, set())
    for ws in set(subscribers):
        try:
            await ws.send_json(payload)
        except Exception:
            # remove dead connections
            subscribers.discard(ws)