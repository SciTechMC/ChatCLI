# app/websockets/services.py

from fastapi import WebSocket, status
from db_helper import fetch_records, insert_record
import logging
import hashlib

# In-memory connection & subscription registries
active_connections: dict[str, WebSocket] = {}
# In-memory: chat_id -> set of WebSocket connections
chat_subscriptions: dict[int, set[WebSocket]] = {}
# In-memory idle list subscriptions
idle_subscriptions: set[WebSocket] = set()

async def authenticate(websocket: WebSocket, msg: dict) -> str | None:
    """
    Token-only auth. Client must send:
      { "type": "auth", "token": "<plain-text session token>" }
    We SHA-256 hash it, then:
      - find a non-revoked, unexpired session_tokens row matching that hash
      - load the user’s username from users
      - register the WS and broadcast status
    """
    # 1) Validate payload
    if msg.get("type") != "auth" or not isinstance(msg.get("token"), str):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    # 2) Hash the incoming plain‐text token
    token_hash = hashlib.sha256(msg["token"].encode()).hexdigest()

    # 3) Look up exactly that session row
    sessions = await fetch_records(
        table="session_tokens",
        where_clause="session_token = %s AND revoked = FALSE AND expires_at > CURRENT_TIMESTAMP()",
        params=(token_hash,),
        fetch_all=True
    )
    if not sessions:
        logging.warning("No matching session token found or it’s expired/revoked.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    user_id = sessions[0]["userID"]

    # 4) Fetch the user’s username
    users = await fetch_records(
        table="users",
        where_clause="userID = %s AND disabled = FALSE AND deleted = FALSE",
        params=(user_id,),
        fetch_all=True
    )
    if not users:
        logging.error("Session token matched, but no user record (or user disabled).")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return None

    username = users[0]["username"]

    # 5) Register and broadcast
    active_connections[username] = websocket
    await notify_status(username, is_online=True)

    logging.info(f"User authenticated: {username} (userID={user_id})")
    return username


async def join_chat(username: str, chat_id: int, ws: WebSocket):
    chat_subscriptions.setdefault(chat_id, set()).add(ws)

async def leave_chat(username: str, chat_id: int, ws: WebSocket):
    chat_subscriptions.get(chat_id, set()).discard(ws)

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
    users = await fetch_records(
        table="users",
        where_clause="username = %s",
        params=(username,),
        fetch_all=True
    )
    if not users:
        return None
    user_id = users[0]["userID"]
    user_name = users[0]["username"]  # Capture the username

    if text.strip() == "":
        logging.warning(f"Empty message from {username} in chat {chat_id}.")
        return {
            "status": "error",
            "code": "EMPTY_MESSAGE",
            "message": "Cannot send an empty message."
        }

    if len(text) > 2048:
        logging.warning(f"Message too long ({len(text)} chars) from {username} in chat {chat_id}.")
        return {
            "status": "error",
            "code": "TOO_LONG",
            "message": f"Message exceeds 2048‐character limit ({len(text)}).",
            "limit": 2048,
            "length": len(text)
        }

    # insert into messages
    message_id = await insert_record(
        "messages",
        {"chatID": chat_id, "userID": user_id, "message": text}
    )

    # re-fetch the row to get timestamp etc.
    rows = await fetch_records(
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
        "username":  user_name,  # Add username to payload
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

async def broadcast_typing(username: str, chat_id: int):
    payload = {
        "type": "user_typing",
        "username": username,
        "chatID": chat_id
    }
    await broadcast_msg(chat_id, payload)

async def notify_status(username: str, is_online: bool):
    payload = {
        "type": "user_status",
        "username": username,
        "online": is_online
    }

    # Notify active chat participants
    for subscribers in chat_subscriptions.values():
        for ws in set(subscribers):
            try:
                await ws.send_json(payload)
            except:
                subscribers.discard(ws)

    # Notify idle listeners too
    for ws in set(idle_subscriptions):
        try:
            await ws.send_json(payload)
        except:
            idle_subscriptions.discard(ws)
