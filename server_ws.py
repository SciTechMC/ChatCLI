import asyncio
import websockets
import json
import aiomysql


async def main(data, ws):
    """
    Handle chat functionality between users via WebSocket.

    :param data: JSON data containing username, receiver, and user_key.
    :param ws: WebSocket connection.
    """
    username = data.get("username")
    receiver = data.get("receiver")
    user_key = data.get("user_key")
    last_msg_id = 0  # Track the latest message ID for incremental fetching

    try:
        # Create a database connection pool
        async with aiomysql.create_pool(
            host="localhost", user="production_chatcli", password="S3cret#Code1234", db="chatcli_prod", minsize=1, maxsize=5
        ) as pool:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # Validate user and their key
                    await cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                    user = await cursor.fetchone()

                    if not user or user["user_key"] != user_key:
                        await ws.send(json.dumps({"error": "Invalid user or key", "status_code": 400}))
                        return

                    # Retrieve the chat ID for the sender and receiver
                    await cursor.execute(
                        """
                        SELECT chatID 
                        FROM Participants 
                        WHERE userID IN (
                            SELECT userID FROM Users WHERE username IN (%s, %s)
                        )
                        GROUP BY chatID
                        HAVING COUNT(DISTINCT userID) = 2;
                        """,
                        (username, receiver)
                    )
                    result = await cursor.fetchone()

                    if not result:
                        await ws.send(json.dumps({"error": "Chat not found", "status_code": 404}))
                        return

                    chat_id = result["chatID"]

                # Continuously fetch and send new messages
                while True:
                    async with conn.cursor(aiomysql.DictCursor) as cursor:
                        # Fetch messages newer than the last processed message
                        await cursor.execute(
                            """
                            SELECT 
                                m.messageID, m.message, m.timestamp, u.username AS user 
                            FROM Messages m
                            JOIN Users u ON m.userID = u.userID
                            WHERE m.chatID = %s AND m.messageID > %s
                            ORDER BY m.messageID ASC
                            LIMIT 200;
                            """,
                            (chat_id, last_msg_id)
                        )
                        messages = await cursor.fetchall()

                        if messages:
                            last_msg_id = max(msg["messageID"] for msg in messages)
                            for msg in messages:
                                msg["timestamp"] = msg["timestamp"].isoformat()  # Convert to ISO format
                                del msg["messageID"]  # Remove internal ID

                            # Send messages to the client
                            await ws.send(json.dumps({"messages": messages, "status_code": 200}))

                        await asyncio.sleep(2)  # Polling delay
                    await conn.commit()

    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        # Ensure the WebSocket connection is closed
        await ws.close()


async def handler(ws):
    """
    Handle incoming WebSocket connections and data.

    :param ws: WebSocket connection.
    """
    print("Client connected.")
    async for message in ws:
        try:
            data = json.loads(message)
            required_keys = ("username", "receiver", "user_key")
            if all(data.get(key) for key in required_keys):
                await main(data, ws)
            else:
                await ws.send(json.dumps({"error": "Invalid data format", "status_code": 400}))
        except json.JSONDecodeError:
            await ws.send(json.dumps({"error": "Malformed JSON", "status_code": 400}))


async def ws_start():
    """
    Start the WebSocket server.
    """
    print("Starting WebSocket server on 0.0.0.0:8765...")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()  # Keep the server running indefinitely


if __name__ == "__main__":
    asyncio.run(ws_start())