import logging
import hashlib
import mysql.connector
from fastapi import WebSocket, status
from db_helper import fetch_records, insert_record

# In-memory connection & subscription registries
active_connections: dict[str, WebSocket] = {}
chat_subscriptions: dict[int, set[WebSocket]] = {}
idle_subscriptions: set[WebSocket] = set()

# Module logger
logger = logging.getLogger(__name__)

async def authenticate(websocket: WebSocket, msg: dict) -> str | None:
    """
    Token-only auth handshake over WebSocket.
    """
    # Validate payload
    if msg.get("type") != "auth" or not isinstance(msg.get("token"), str):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    # Hash token
    token_plain = msg["token"]
    token_hash = hashlib.sha256(token_plain.encode()).hexdigest()

    # Lookup session
    try:
        sessions = await fetch_records(
            table="session_tokens",
            where_clause="session_token = %s AND revoked = FALSE AND expires_at > CURRENT_TIMESTAMP()",
            params=(token_hash,),
            fetch_all=True
        )
    except mysql.connector.Error as e:
        logger.error("DB error during session lookup: %s", e, exc_info=e)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return None
    except Exception as e:
        logger.error("Unexpected error during session lookup: %s", e, exc_info=e)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return None

    if not sessions:
        logger.warning("Invalid or expired session token.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    user_id = sessions[0]["userID"]

    # Fetch user record
    try:
        users = await fetch_records(
            table="users",
            where_clause="userID = %s AND disabled = FALSE AND deleted = FALSE",
            params=(user_id,),
            fetch_all=True
        )
    except mysql.connector.Error as e:
        logger.error("DB error during user lookup: %s", e, exc_info=e)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return None
    except Exception as e:
        logger.error("Unexpected error during user lookup: %s", e, exc_info=e)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return None

    if not users:
        logger.error("Session valid but no active user found (userID=%s).", user_id)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return None

    username = users[0]["username"]

    # Register connection and broadcast online
    active_connections[username] = websocket
    try:
        await notify_status(username, is_online=True)
    except Exception as e:
        logger.warning("Failed to notify status for %s: %s", username, e, exc_info=e)

    logger.info("User authenticated: %s (userID=%s)", username, user_id)
    return username

async def join_chat(username: str, chat_id: int, ws: WebSocket):
    try:
        chat_subscriptions.setdefault(chat_id, set()).add(ws)
        logger.debug("%s joined chat %s", username, chat_id)
    except Exception as e:
        logger.error("Error adding %s to chat %s: %s", username, chat_id, e, exc_info=e)

async def leave_chat(username: str, chat_id: int, ws: WebSocket):
    try:
        chat_subscriptions.get(chat_id, set()).discard(ws)
        logger.debug("%s left chat %s", username, chat_id)
    except Exception as e:
        logger.error("Error removing %s from chat %s: %s", username, chat_id, e, exc_info=e)

async def post_msg(msg: dict) -> dict | None:
    """
    Inserts and broadcasts a message.
    Returns the payload or error payload dict.
    """
    username = msg.get("username", "").lower()
    chat_id = msg.get("chatID")
    text = msg.get("text", "")

    # Validate inputs
    if not username or chat_id is None or text is None:
        return None

    # Fetch userID
    try:
        users = await fetch_records(
            table="users",
            where_clause="username = %s",
            params=(username,),
            fetch_all=True
        )
    except mysql.connector.Error as e:
        logger.error("DB error fetching user %s: %s", username, e, exc_info=e)
        return {"status": "error", "code": "DB_ERROR", "message": "Internal server error."}
    except Exception as e:
        logger.error("Unexpected error fetching user %s: %s", username, e, exc_info=e)
        return {"status": "error", "code": "INTERNAL_ERROR", "message": "Internal server error."}

    if not users:
        return {"status": "error", "code": "USER_NOT_FOUND", "message": "User not found."}
    user_rec = users[0]
    user_id = user_rec["userID"]
    display_name = user_rec.get("username", username)

    # Validate text
    if not text.strip():
        logger.warning("Empty message from %s in chat %s", username, chat_id)
        return {"status": "error", "code": "EMPTY_MESSAGE", "message": "Cannot send an empty message."}
    if len(text) > 2048:
        logger.warning("Message too long (%s chars) from %s in chat %s", len(text), username, chat_id)
        return {"status": "error", "code": "TOO_LONG", "message": "Message exceeds 2048-character limit.", "limit": 2048, "length": len(text)}

    # Insert message
    try:
        message_id = await insert_record(
            "messages",
            {"chatID": chat_id, "userID": user_id, "message": text}
        )
    except mysql.connector.Error as e:
        logger.error("DB error inserting message for %s: %s", username, e, exc_info=e)
        return {"status": "error", "code": "DB_ERROR", "message": "Internal server error."}
    except Exception as e:
        logger.error("Unexpected error inserting message for %s: %s", username, e, exc_info=e)
        return {"status": "error", "code": "INTERNAL_ERROR", "message": "Internal server error."}

    # Fetch inserted
    try:
        rows = await fetch_records(
            table="messages",
            where_clause="messageID = %s",
            params=(message_id,),
            fetch_all=True
        )
    except Exception as e:
        logger.error("Error fetching inserted message %s: %s", message_id, e, exc_info=e)
        return None

    if not rows:
        return None
    row = rows[0]

    payload = {
        "type": "new_message",
        "messageID": row["messageID"],
        "chatID": row["chatID"],
        "userID": row["userID"],
        "username": display_name,
        "message": row["message"],
        "timestamp": row["timestamp"].isoformat()
    }

    await broadcast_msg(chat_id, payload)
    return payload

async def broadcast_msg(chat_id: int, payload: dict):
    """
    Send payload to subscribers of chat_id.
    """
    subscribers = chat_subscriptions.get(chat_id, set())
    for ws in set(subscribers):
        try:
            await ws.send_json(payload)
        except Exception as e:
            logger.warning("Removing dead connection in chat %s: %s", chat_id, e)
            subscribers.discard(ws)

async def broadcast_typing(username: str, chat_id: int):
    payload = {"type": "user_typing", "username": username, "chatID": chat_id}
    await broadcast_msg(chat_id, payload)

async def notify_status(username: str, is_online: bool):
    payload = {"type": "user_status", "username": username, "online": is_online}

    # Notify chat participants
    for subs in chat_subscriptions.values():
        for ws in set(subs):
            try:
                await ws.send_json(payload)
            except Exception as e:
                logger.warning("Removing dead connection in status notify: %s", e)
                subs.discard(ws)

    # Notify idle subscriptions
    for ws in set(idle_subscriptions):
        try:
            await ws.send_json(payload)
        except Exception as e:
            logger.warning("Removing dead idle connection: %s", e)
            idle_subscriptions.discard(ws)