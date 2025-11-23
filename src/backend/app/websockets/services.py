import logging
import hashlib
import mysql.connector
from fastapi import WebSocket, status
from db_helper import fetch_records, insert_record
import uuid
import calls

logger = logging.getLogger(__name__)

# In-memory connection & subscription registries
active_connections: dict[str, WebSocket] = {} # username -> WebSocket ; stores all active ws connections
chat_subscriptions: dict[int, set[WebSocket]] = {} # chatID -> set of WebSockets ; stores ws connections subscribed to each chat
idle_subscriptions: set[WebSocket] = set() # stores ws connections subscribed to idle notifications
pending_calls: dict[int, dict] = {}
call_sessions: dict[str, dict] = {}
user_status: dict[str, bool] = {} # username -> online status (True/False)

def reset_variables():
    """
    Resets all in-memory variables. Used on server startup.
    """
    global active_connections, chat_subscriptions, idle_subscriptions, pending_calls, call_sessions, user_status
    active_connections = {}
    chat_subscriptions = {}
    idle_subscriptions = set()
    pending_calls = {}
    call_sessions = {}
    user_status = {}

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

    logger.info("User authenticated: %s (userID=%s)", username, user_id)
    return username

async def join_chat(username: str, chat_id: int, ws: WebSocket):
    try:
        chat_subscriptions.setdefault(chat_id, set()).add(ws)
        await emit_call_state(ws, chat_id)
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
    """
    Notify only users related to the given user about their status change.
    Updates the global user_status dictionary.
    """
    try:
        # Update the user_status dictionary
        user_status[username] = is_online

        # Fetch all chat IDs the user is part of
        user_chats = await fetch_records(
            table="participants",
            where_clause="userID = (SELECT userID FROM users WHERE username = %s)",
            params=(username,),
            fetch_all=True
        )
        chat_ids = {row["chatID"] for row in user_chats}

        # Fetch all usernames of participants in those chats
        related_users = set()
        for chat_id in chat_ids:
            participants = await fetch_records(
                table="participants",
                where_clause="chatID = %s",
                params=(chat_id,),
                fetch_all=True
            )
            related_users.update(
                row["userID"] for row in participants if row["userID"] != username
            )

        # Fetch usernames for related user IDs
        related_usernames = []
        for user_id in related_users:
            user_row = await fetch_records(
                table="users",
                where_clause="userID = %s AND disabled = FALSE AND deleted = FALSE",
                params=(user_id,),
                fetch_all=False
            )
            if user_row:
                related_usernames.append(user_row["username"])

        # Notify only related users
        payload = {"type": "user_status", "username": username, "online": is_online}
        for related_username in related_usernames:
            ws = active_connections.get(related_username)
            if ws:
                try:
                    await ws.send_json(payload)
                except Exception as e:
                    logger.warning("Removing dead connection for %s: %s", related_username, e)
                    active_connections.pop(related_username, None)
    except Exception as e:
        logger.error("Failed to notify status for %s: %s", username, e, exc_info=e)

async def get_online_users_for_user(username: str) -> list[str]:
    """
    Get a list of online users who share common chats with the given user.
    """
    try:
        # Fetch all chat IDs the user is part of
        user_chats = await fetch_records(
            table="participants",
            where_clause="userID = (SELECT userID FROM users WHERE username = %s)",
            params=(username,),
            fetch_all=True
        )
        chat_ids = {row["chatID"] for row in user_chats}

        # Fetch all usernames of participants in those chats
        related_users = set()
        for chat_id in chat_ids:
            participants = await fetch_records(
                table="participants",
                where_clause="chatID = %s",
                params=(chat_id,),
                fetch_all=True
            )
            related_users.update(
                row["userID"] for row in participants if row["userID"] != username
            )

        # Fetch usernames for related user IDs
        online_users = []
        for user_id in related_users:
            user_row = await fetch_records(
                table="users",
                where_clause="userID = %s AND disabled = FALSE AND deleted = FALSE",
                params=(user_id,),
                fetch_all=False
            )
            if user_row and user_status.get(user_row["username"], False):
                online_users.append(user_row["username"])

        return online_users
    except Exception as e:
        logger.error("Failed to get online users for %s: %s", username, e, exc_info=e)
        return []

async def emit_call_state(ws: WebSocket, chat_id: int) -> None:
    """Send current call state for a chat to a single websocket, if any."""
    call_id = pending_calls.get(chat_id)
    if not call_id:
        return
    session = call_sessions.get(call_id)
    if not session:
        return
    await ws.send_json({
        "type": "call_state",
        "chatID": chat_id,
        "call_id": call_id,
        "initiator": session.get("initiator"),
        "state": session.get("state", "ringing"),
    })

async def broadcast_chat_created(chat_id: int, creator_username: str):
    """
    Broadcast 'chat_created' to all participants of the chat except the creator.
    """
    try:
        # Step 1: fetch userIDs of participants
        participants_rows = await fetch_records(
            table="participants",
            where_clause="chatID = %s",
            params=(chat_id,)
        )
        if not participants_rows:
            return

        user_ids = [row["userID"] for row in participants_rows]

        # Step 2: fetch usernames for those userIDs
        usernames = []
        for uid in user_ids:
            user_row = await fetch_records(
                table="users",
                where_clause="userID = %s AND disabled = FALSE AND deleted = FALSE",
                params=(uid,),
                fetch_all=False
            )
            if user_row:
                usernames.append(user_row["username"])

        payload = {
            "type": "chat_created",
            "chatID": chat_id,
            "creator": creator_username,
        }

        for username in usernames:
            if username == creator_username:
                continue
            ws = active_connections.get(username)
            if ws:
                try:
                    await ws.send_json(payload)
                except Exception as e:
                    logging.warning("Failed to send chat_created to %s: %s", username, e)
                    active_connections.pop(username, None)

    except Exception as e:
        logging.error("Failed to broadcast chat_created: %s", e)

async def handle_message(username: str, ws: WebSocket, msg: dict) -> None:
    """
    Route a single inbound WebSocket message for a given user.
    """
    logger.debug("Received message for %s: %s", username, msg)

    try:
        match msg:
            # ----- CHAT MESSAGES / PRESENCE -----

            case {"type": "join_chat", "chatID": chat_id}:
                await join_chat(username, chat_id, ws)

            case {"type": "leave_chat", "chatID": chat_id}:
                await leave_chat(username, chat_id, ws)

            case {"type": "post_msg", "chatID": chat_id, "text": text} if isinstance(text, str):
                result = await post_msg({
                    "username": username,
                    "chatID":   chat_id,
                    "text":     text,
                })
                await ws.send_json({
                    "type":      "post_msg_ack",
                    "status":    "ok",
                    "messageID": result.get("messageID") if isinstance(result, dict) else None,
                })

            case {"type": "typing", "chatID": chat_id}:
                await broadcast_typing(username, chat_id)

            case {"type": "chat_created", "chatID": chat_id, "creator": creator}:
                await broadcast_chat_created(chat_id, creator)

            case {"type": "join_idle"}:
                idle_subscriptions.add(ws)

            # ----- CALLING CASES -----

            case {"type": "call_invite", "chatID": chat_id}:
                await calls.call_invite(caller=username, chat_id=chat_id)

            case {"type": "call_accept", "chatID": chat_id, "call_id": call_id}:
                await calls.call_accept(username=username, chat_id=chat_id, call_id=call_id)

            case {"type": "call_decline", "chatID": chat_id}:
                await calls.call_decline(username=username, chat_id=chat_id)

            case {"type": "call_end", "chatID": chat_id}:
                await calls.call_end(username=username, chat_id=chat_id)

            # ----- FALLBACKS -----

            # Known shape but unsupported action
            case {"type": action}:
                raise ValueError(f"Unknown action: {action}")

            # Completely invalid payload
            case _:
                raise ValueError("Invalid message payload")

    except ValueError as ve:
        logger.warning("Value error for user %s: %s", username, ve)
        try:
            await ws.send_json({"type": "error", "message": str(ve)})
        except RuntimeError:
            # WebSocket already closed; nothing else to do
            pass
    except Exception as e:
        logger.error("Error handling message for %s: %s", username, e, exc_info=e)
        try:
            await ws.send_json({"type": "error", "message": "Internal server error"})
        except RuntimeError:
            # WebSocket already closed
            pass

async def cleanup_connection(username: str, ws: WebSocket) -> None:
    """
    Remove this websocket from all registries and mark the user offline.
    Safe to call even if things are already partially cleaned up.
    """
    # Remove from all chat subscriptions
    for subs in chat_subscriptions.values():
        subs.discard(ws)

    # Remove from idle subscriptions
    idle_subscriptions.discard(ws)

    # Remove from active_connections *only if* this ws is still the one stored
    current_ws = active_connections.get(username)
    if current_ws is ws:
        active_connections.pop(username, None)

    # Notify others the user is offline (also updates user_status)
    try:
        await notify_status(username, is_online=False)
    except Exception as e:
        logger.error("Failed to notify status for %s: %s", username, e, exc_info=e)