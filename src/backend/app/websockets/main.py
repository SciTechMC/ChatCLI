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
)
import uvicorn

# Configure module logger
logger = logging.getLogger(__name__)

app = FastAPI()

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
        logger.info("Authentication result for %s: %s", init, username)
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
        logger.info("Authentication acknowledged for user: %s", username)
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

@app.websocket("/call/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    connections[username] = websocket

    try:
        while True:
            data = await websocket.receive_json()
            target = data.get("to")
            if target in connections:
                await connections[target].send_json({
                    "from": username,
                    "type": data["type"],
                    "data": data.get("data")
                })
    except WebSocketDisconnect:
        del connections[username]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")