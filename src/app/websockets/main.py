from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.websockets.services import authenticate, join_chat, leave_chat, post_msg, chat_subscriptions

app = FastAPI()

@app.websocket("/ws/chat")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    # 1) Auth handshake
    init = await ws.receive_json()
    username = await authenticate(ws, init)
    if not username:
        return
    await ws.send_json({"type": "auth_ack", "status": "ok"})

    # 2) Main loop
    try:
        while True:
            msg = await ws.receive_json()
            t   = msg.get("type")

            if t == "join_chat":
                await join_chat(username, msg.get("chatID"))

            elif t == "leave_chat":
                await leave_chat(username, msg.get("chatID"))

            elif t == "chat_message":
                await post_msg({
                    "username": username,
                    "chatID":   msg.get("chatID"),
                    "text":     msg.get("text")
                })

            else:
                await ws.send_json({
                    "type":    "error",
                    "message": f"Unknown action: {t}"
                })

    except WebSocketDisconnect:
        # clean up any subscriptions
        for subs in chat_subscriptions.values():
            subs.discard(ws)