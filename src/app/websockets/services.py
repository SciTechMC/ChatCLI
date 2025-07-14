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
      { "type":"auth", "token":"<plain-text session token>" }

    We SHA-256 hash the incoming token, compare it against
    `session_tokens.session_token`, load the user’s username,
    register the WS, and return it. Otherwise we close immediately.
    """
    token = msg.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    # 1) Hash the incoming plain-text token with SHA-256
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    # 2) Fetch all non-revoked, unexpired sessions
    sessions = await fetch_records(
        table="session_tokens",
        where_clause="revoked = FALSE AND expires_at > CURRENT_TIMESTAMP()",
        fetch_all=True
    )

    # 3) Find a matching SHA-256 hash
    matched = next((s for s in sessions if s["session_token"] == token_hash), None)
    if not matched:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    # 4) Lookup the username for that session’s userID
    users = await fetch_records(
        table="users",
        where_clause="userID = %s",
        params=(matched["userID"],),
        fetch_all=True
    )
    if not users:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return None

    username = users[0]["username"]

    # 5) Register the connection
    active_connections[username] = websocket

    # 6) Broadcast that this user is online
    await notify_status(username, is_online=True)

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
