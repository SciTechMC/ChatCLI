import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from services import (
    authenticate,
    join_chat,
    leave_chat,
    post_msg,
    chat_subscriptions,
    broadcast_typing,
    notify_status,
    active_connections,
    idle_subscriptions,
    call_invite,
    call_accept,
    call_decline,
    call_end,
    call_sessions,
)
import uvicorn

# Configure module logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('app.log', mode='w'),
        logging.StreamHandler()
    ]
)
# Logging level priority (low → high)
# NOTSET   = 0   → disables filtering
# DEBUG    = 10  → detailed debug info
# INFO     = 20  → general runtime events
# WARNING  = 30  → unexpected but non-fatal issues
# ERROR    = 40  → serious problems in execution
# CRITICAL = 50  → severe errors; program may fail

app = FastAPI()
call_rooms: dict[str, set[WebSocket]] = {}

call_users: dict[str, set[str]] = {}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    # Accept connection
    await ws.accept()
    logger.info("WebSocket connection accepted.")

    # Authentication handshake
    try:
        init = await ws.receive_json()
        logger.debug("Received auth payload: %s", init)
    except Exception as e:
        logger.error("Failed to receive auth payload", exc_info=e)
        await ws.close(code=1003)
        return

    try:
        username = await authenticate(ws, init)
    except Exception as e:
        logger.error("Error during authentication", exc_info=e)
        try:
            await ws.send_json({"type": "error", "message": "Authentication error"})
        except RuntimeError:
            # Connection already closed, ignore send error
            pass
        await ws.close(code=1008)
        return

    if not username:
        logger.warning("Invalid credentials: %s", init)
        return

    # Acknowledge successful auth
    try:
        await ws.send_json({"type": "auth_ack", "status": "ok"})
        #logger.info("Authentication acknowledged for user: %s", username)
        active_connections[username] = ws
    except RuntimeError:
        await ws.close(code=1008)
        return

    # Main message loop
    try:
        while True:
            try:
                msg = await ws.receive_json()
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected for user: %s", username)
                break  # Exit the loop cleanly

            msg_type = msg.get("type")
            logger.debug("Received message for %s: %s", username, msg)


            try:
                if msg_type == "join_chat":
                    await join_chat(username, msg.get("chatID"), ws)
                elif msg_type == "leave_chat":
                    await leave_chat(username, msg.get("chatID"), ws)
                elif msg_type == "post_msg":
                    result = await post_msg({
                        "username": username,
                        "chatID": msg.get("chatID"),
                        "text": msg.get("text")
                    })
                    await ws.send_json({
                        "type":        "post_msg_ack",
                        "status":      "ok",
                        "messageID":   result.get("messageID") if result else None
                    }) 
                elif msg_type == "typing":
                    await broadcast_typing(username, msg.get("chatID"))
                elif msg_type == "join_idle":
                    idle_subscriptions.add(ws)
                elif msg_type == "call_invite":
                    logger.info("Call invite from %s to %s in chat %s", username, msg.get("callee"), msg.get("chatID"))
                    await call_invite(caller=username, chat_id=msg.get("chatID"), callee=msg.get("callee"))
                elif msg_type == "call_accept":
                    await call_accept(username=username, chat_id=msg.get("chatID"))
                elif msg_type == "call_decline":
                    await call_decline(username=username, chat_id=msg.get("chatID"))
                elif msg_type == "call_end":
                    await call_end(username=username, chat_id=msg.get("chatID"))
                else:
                    raise ValueError(f"Unknown action: {msg_type}")
            except ValueError as ve:
                logger.warning("Value error for user %s: %s", username, ve)
                try:
                    await ws.send_json({"type": "error", "message": str(ve)})
                except RuntimeError:
                    break
            except Exception as e:
                logger.error("Error handling message for %s: %s", username, e, exc_info=e)
                try:
                    await ws.send_json({"type": "error", "message": "Internal server error"})
                except RuntimeError:
                    break
    except Exception as e:
        logger.error("Unexpected error in connection loop for %s", username, exc_info=e)
    finally:
        # Clean up subscriptions
        for subs in chat_subscriptions.values():
            subs.discard(ws)

        # Remove from active connections
        active_connections.pop(username, None)
        idle_subscriptions.discard(ws)

        # Notify others the user is offline
        try:
            await notify_status(username, is_online=False)
        except Exception as e:
            logger.error("Failed to notify status for %s: %s", username, e, exc_info=e)

from fastapi.middleware.cors import CORSMiddleware
connections = {}  # username -> WebSocket
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/call/{call_id}/{user}")
async def call_ws(ws: WebSocket, call_id: str, user: str):
    await ws.accept()

    sess = call_sessions.get(call_id)
    if sess and user not in {sess.get("from"), sess.get("to")}:
        await ws.close(code=1008)
        return

    call_rooms.setdefault(call_id, set()).add(ws)
    call_users.setdefault(call_id, set()).add(user)

    try:
        while True:
            data = await ws.receive_json()
            # Attach sender; fan out to other participant(s) in this call
            data["from"] = user
            for peer in list(call_rooms.get(call_id, set())):
                if peer is not ws:
                    await peer.send_json(data)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            for peer in list(call_rooms.get(call_id, set())):
                if peer is not ws:
                    await peer.send_json({"type": "leave", "by": user})
        except Exception:
            pass

        room = call_rooms.get(call_id, set())
        room.discard(ws)
        if not room:
            call_rooms.pop(call_id, None)
            call_users.pop(call_id, None)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info", use_colors=False)