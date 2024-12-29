import asyncio
import websockets
import json
import aiomysql  # Asynchronous MySQL client

async def main(data, ws):
    username = data.get("username")
    receiver = data.get("receiver")
    key = data.get("user_key")
    last_msg_id = 0  # Start with no messages sent

    try:
        # Database connection (using aiomysql for async)
        async with aiomysql.create_pool(
            host="localhost", user="chatcli_access", password="test1234", database="chatcli", minsize=1, maxsize=5
        ) as pool:
            async with pool.acquire() as conn:
                async with conn.cursor(dictionary=True) as cursor:
                    # Validate user and key
                    await cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                    user = await cursor.fetchone()
                    if not user or user['user_key'] != key:
                        await ws.send(json.dumps({"error": "Invalid user or key", "status_code": 400}))
                        await ws.close()
                        return

                    # Fetch chat details
                    await cursor.execute("""
                        SELECT chatID FROM Participants 
                        WHERE userID IN (
                            SELECT userID FROM Users WHERE username = %s
                        ) AND userID IN (
                            SELECT userID FROM Users WHERE username = %s
                        );
                    """, (username, receiver))
                    result = await cursor.fetchone()

                    if not result:
                        await ws.send(json.dumps({"error": "Chat not found", "status_code": 404}))
                        await ws.close()
                        return

                    chat_id = result['chatID']

                    # Fetch initial 200 messages
                    while True:
                        await cursor.execute("""
                            SELECT messageID, userID, message 
                            FROM Messages 
                            WHERE chatID = %s AND messageID > %s 
                            ORDER BY messageID DESC LIMIT 200;
                        """, (chat_id, last_msg_id))

                        messages = await cursor.fetchall()
                        if messages:
                            last_msg_id = max(msg["messageID"] for msg in messages)
                            for msg in messages:
                                msg["user"] = username if msg["userID"] == user["userID"] else receiver
                                del msg["userID"]
                                del msg["messageID"]

                            await ws.send(json.dumps({"messages": messages}))
                        await asyncio.sleep(2)  # Pause between fetches to reduce load

    except aiomysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        await ws.send(json.dumps({"error": "Internal server error", "status_code": 500}))
    finally:
        pass  # No need for cursor.close() as the context manager handles it

async def handler(websocket):
    # Handle incoming messages or connections here
    async for client in websocket:
        data = json.loads(client)
        if data and data.get("username") and data.get("receiver") and data.get("user_key"):
            await main(data, websocket)

async def ws_start():
    async with websockets.serve(handler, "0.0.0.0", 6420):
        print(f"WebSocket server running on 0.0.0.0:6420")
        await asyncio.Future()  # Keeps the server running indefinitely

if __name__ == "__main__":
    asyncio.run(ws_start())