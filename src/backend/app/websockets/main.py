# main.py
import logging
import json
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

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

logger = logging.getLogger(__name__)
app = FastAPI()

# --------------------------------------------------------------------------------------
# CORS (unchanged)
# --------------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------------------
# Call Registry (new)
# --------------------------------------------------------------------------------------
@dataclass
class CallRoom:
    ongoing: bool = False
    caller: Optional[str] = None
    started_at: Optional[float] = None
    last_offer: Optional[dict] = None                  # store the most recent SDP offer
    participants: Set[str] = field(default_factory=set)  # usernames currently in the room

# Keyed by chatID as a string (matches /ws/{room}/{user} path)
CALL_ROOMS: Dict[str, CallRoom] = {}

# In-memory per-chat signaling sockets (as you had before)
rooms: Dict[str, list[WebSocket]] = {}


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
async def _broadcast_to_room(room_id: str, msg: dict, exclude: Optional[WebSocket] = None):
    """Fan-out a JSON message to everyone in the signaling room except 'exclude'."""
    for ws in rooms.get(room_id, []):
        if ws is exclude:
            continue
        try:
            await ws.send_json(msg)
        except Exception:
            # ignore send errors; disconnect cleanup happens elsewhere
            pass


async def _broadcast_global_incoming(chat_id: str, caller: str):
    payload = {
        "type": "incoming_call",
        "chatID": int(chat_id) if chat_id.isdigit() else chat_id,
        "caller": caller,
        "startedAt": int(time.time()),
    }

    targets: Set[WebSocket] = set()

    # WS of the caller (so we can exclude it)
    caller_ws = active_connections.get(caller)

    # People currently viewing this chat (if you track them)
    try:
        cid_int = int(chat_id) if chat_id.isdigit() else None
        if cid_int is not None and cid_int in chat_subscriptions:
            for ws in chat_subscriptions[cid_int]:
                if ws is not caller_ws:
                    targets.add(ws)
    except Exception:
        pass

    # Everyone online on the global bus (exclude caller)
    for user, ws in active_connections.items():
        if user != caller:
            targets.add(ws)

    # Anyone on the idle/global notifications bus (exclude caller if present)
    for ws in idle_subscriptions:
        if ws is not caller_ws:
            targets.add(ws)

    for ws in list(targets):
        try:
            await ws.send_json(payload)
        except Exception:
            pass

# --------------------------------------------------------------------------------------
# Global WebSocket: /ws  (unchanged except for cleanup)
# --------------------------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    logger.info("Global WebSocket accepted")

    # --- Authentication handshake ---
    try:
        init = await ws.receive_json()
    except Exception as e:
        logger.error("Failed to receive auth payload", exc_info=e)
        await ws.close(code=1003)
        return

    try:
        username = await authenticate(ws, init)
    except Exception as e:
        logger.error("Auth error", exc_info=e)
        try:
            await ws.send_json({"type": "error", "message": "Authentication error"})
        except RuntimeError:
            pass
        await ws.close(code=1008)
        return

    if not username:
        logger.warning("Invalid credentials")
        return

    # Acknowledge auth
    try:
        await ws.send_json({"type": "auth_ack", "status": "ok"})
        active_connections[username] = ws
    except RuntimeError:
        await ws.close(code=1008)
        return

    # --- Message loop ---
    try:
        while True:
            try:
                msg = await ws.receive_json()
            except WebSocketDisconnect:
                logger.info("Global WS disconnected: %s", username)
                break

            msg_type = msg.get("type")

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
                        "type":      "post_msg_ack",
                        "status":    "ok",
                        "messageID": result.get("messageID") if result else None
                    })

                elif msg_type == "typing":
                    await broadcast_typing(username, msg.get("chatID"))

                elif msg_type == "join_idle":
                    idle_subscriptions.add(ws)

                elif msg_type == "call_decline":
                    # Optional: notify the room/caller
                    chat_id = msg.get("chatID")
                    if chat_id is not None:
                        room_id = str(chat_id)
                        await _broadcast_to_room(room_id, {
                            "type": "call_declined",
                            "by": username,
                            "chatID": chat_id
                        })

                else:
                    # Keep unknowns explicit to surface client bugs
                    await ws.send_json({"type": "error", "message": f"Unknown action: {msg_type}"})

            except Exception as e:
                logger.error("Error handling global msg for %s: %s", username, e, exc_info=e)
                try:
                    await ws.send_json({"type": "error", "message": "Internal server error"})
                except RuntimeError:
                    break

    finally:
        # --- Cleanup ---
        for subs in chat_subscriptions.values():
            subs.discard(ws)
        idle_subscriptions.discard(ws)
        active_connections.pop(username, None)
        try:
            await notify_status(username, is_online=False)
        except Exception as e:
            logger.error("Failed to notify offline for %s: %s", username, e, exc_info=e)


# --------------------------------------------------------------------------------------
# Per-chat Call WebSocket: /ws/{room}/{user}
# Adds: call_state snapshot, last_offer storage, global incoming_call
# --------------------------------------------------------------------------------------
async def _register_room_socket(room_id: str, ws: WebSocket):
    rooms.setdefault(room_id, []).append(ws)


async def _unregister_room_socket(room_id: str, ws: WebSocket):
    try:
        rooms[room_id].remove(ws)
        if not rooms[room_id]:
            del rooms[room_id]
    except Exception:
        pass


@app.websocket("/ws/{room}/{user}")
async def ws_call_endpoint(ws: WebSocket, room: str, user: str):
    """
    Minimal signaling socket with a little bit of state:
      - Immediately sends 'call_state' so late joiners can answer
      - Stores last_offer so no re-offer is needed on late join
      - Broadcasts 'incoming_call' globally when a call starts
    """
    await ws.accept()
    await _register_room_socket(room, ws)

    # Ensure a CallRoom exists
    call_room = CALL_ROOMS.get(room)
    if call_room is None:
        call_room = CALL_ROOMS[room] = CallRoom()

    # Track participant by username (best-effort; this endpoint is still lightweight)
    call_room.participants.add(user)

    # Send initial call_state snapshot (late-join safety)
    try:
        await ws.send_json({
            "type": "call_state",
            "ongoing": call_room.ongoing,
            "caller": call_room.caller,
            "startedAt": int(call_room.started_at or 0),
            "latestOffer": call_room.last_offer,
        })
    except Exception:
        # If we fail to send, we still keep the socket open—client may retry.
        pass

    try:
        while True:
            try:
                data = await ws.receive_json()
            except WebSocketDisconnect:
                logger.info("Call WS disconnected: room=%s user=%s", room, user)
                break

            # Optional lightweight auth handwave (client sends token)
            if data.get("type") == "auth":
                # TODO: validate token + membership if you want to harden this path
                continue

            mtype = data.get("type")

            # Caller pressed Start
            if mtype == "call-started":
                if not call_room.ongoing:
                    call_room.ongoing = True
                    call_room.caller = data.get("from") or user
                    call_room.started_at = time.time()
                    call_room.last_offer = None
                    # Global popup so users in other chats hear/see it
                    await _broadcast_global_incoming(room, call_room.caller)

                await _broadcast_to_room(room, data, exclude=None)
                continue

            # Store latest SDP offer for late joiners
            if mtype == "offer" and data.get("sdp"):
                call_room.last_offer = data["sdp"]
                await _broadcast_to_room(room, data, exclude=ws)
                continue

            # Regular signaling passthrough
            if mtype in ("answer", "ice-candidate"):
                await _broadcast_to_room(room, data, exclude=ws)
                continue

            # Someone leaves the call
            if mtype == "leave":
                await _broadcast_to_room(room, data, exclude=ws)
                if user in call_room.participants:
                    call_room.participants.remove(user)
                if not call_room.participants:
                    # Tear down the room state when last leaves
                    call_room.ongoing = False
                    call_room.caller = None
                    call_room.started_at = None
                    call_room.last_offer = None
                continue

            # Optional: explicit call_state request (client fallback)
            if mtype == "get_call_state":
                await ws.send_json({
                    "type": "call_state",
                    "ongoing": call_room.ongoing,
                    "caller": call_room.caller,
                    "startedAt": int(call_room.started_at or 0),
                    "latestOffer": call_room.last_offer,
                })
                continue

            # Unknown type → forward to others (best-effort)
            await _broadcast_to_room(room, data, exclude=ws)

    finally:
        # Cleanup on socket close
        await _unregister_room_socket(room, ws)
        try:
            call_room.participants.discard(user)
            if not call_room.participants:
                call_room.ongoing = False
                call_room.caller = None
                call_room.started_at = None
                call_room.last_offer = None
        except Exception:
            pass


# --------------------------------------------------------------------------------------
# Dev runner
# --------------------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
