import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import services
import uvicorn

# Configure module logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

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
        username = await services.authenticate(ws, init)
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
        services.active_connections[username] = ws
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
                break

            logger.debug("Received message for %s: %s", username, msg)

            try:
                match msg:
                    case {"type": "join_chat", "chatID": chat_id}:
                        await services.join_chat(username, chat_id, ws)

                    case {"type": "leave_chat", "chatID": chat_id}:
                        await services.leave_chat(username, chat_id, ws)

                    case {"type": "post_msg", "chatID": chat_id, "text": text} if isinstance(text, str):
                        result = await services.post_msg({
                            "username": username,
                            "chatID":   chat_id,
                            "text":     text
                        })
                        await ws.send_json({
                            "type":      "post_msg_ack",
                            "status":    "ok",
                            "messageID": result.get("messageID") if result else None
                        })

                    case {"type": "typing", "chatID": chat_id}:
                        await services.broadcast_typing(username, chat_id)

                    case {"type": "chat_created", "chatID": chat_id, "creator": creator}:
                        await services.broadcast_chat_created(chat_id, creator)


                    #------ CALLING CASES ------#

                    case {"type": "join_idle"}:
                        services.idle_subscriptions.add(ws)

                    case {"type": "call_invite", "chatID": chat_id, "callee": callee}:
                        logger.info("Call invite from %s to %s in chat %s", username, callee, chat_id)
                        await services.call_invite(caller=username, chat_id=chat_id, callee=callee)

                    case {"type": "call_accept", "chatID": chat_id}:
                        await services.call_accept(username=username, chat_id=chat_id)

                    case {"type": "call_decline", "chatID": chat_id}:
                        await services.call_decline(username=username, chat_id=chat_id)

                    case {"type": "call_end", "chatID": chat_id}:
                        await services.call_end(username=username, chat_id=chat_id)

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
        for subs in services.chat_subscriptions.values():
            subs.discard(ws)

        # Remove from active connections
        services.active_connections.pop(username, None)
        services.idle_subscriptions.discard(ws)

        # Notify others the user is offline
        try:
            await services.notify_status(username, is_online=False)
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

    sess = services.call_sessions.get(call_id)
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