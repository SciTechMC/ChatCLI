from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from services import authenticate, join_chat, leave_chat, post_msg, chat_subscriptions
import uvicorn

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    print("WebSocket connection accepted.")

    # 1) Auth handshake
    init = await ws.receive_json()
    print(f"Received auth payload: {init}")
    username = await authenticate(ws, init)
    print(f"Authentication result: {username}")
    if not username:
        print("Authentication failed.")
        return
    await ws.send_json({"type": "auth_ack", "status": "ok"})
    print("Authentication acknowledged.")

    # 2) Main loop
    try:
        while True:
            msg = await ws.receive_json()
            t   = msg.get("type")
            print(f"Received message: {msg}")

            if t == "join_chat":
                print(f"{username} joining chat {msg.get('chatID')}")
                await join_chat(username, msg.get("chatID"), ws)

            elif t == "leave_chat":
                print(f"{username} leaving chat {msg.get('chatID')}")
                await leave_chat(username, msg.get("chatID"), ws)

            elif t == "post_msg":
                print(f"{username} posting message to chat {msg.get('chatID')}: {msg.get('text')}")
                await post_msg({
                    "username": username,
                    "chatID":   msg.get("chatID"),
                    "text":     msg.get("text")
                })

            else:
                print(f"Unknown action: {t}")
                await ws.send_json({
                    "type":    "error",
                    "message": f"Unknown action: {t}"
                })

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for user: {username}")
        # clean up any subscriptions
        for subs in chat_subscriptions.values():
            subs.discard(ws)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")