import asyncio
import bcrypt
import websockets
import json
import aiomysql
import db_envs
import ssl

env = db_envs.prod()

async def main(data, ws):
    """
    Handle chat functionality between users via WebSocket.

    :param data: JSON data containing username, receiver, and session_token.
    :param ws: WebSocket connection.
    """
    username = data.get("username")
    receiver = data.get("receiver")
    session_token = data.get("session_token")
    last_msg_id = 0  # Track the latest message ID for incremental fetching

    try:
        # Create a database connection pool
        async with aiomysql.create_pool(
            host="localhost", user=env["user"], password=env["password"], db=env["db"], minsize=1, maxsize=5
        ) as pool:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # Validate user with session token
                    await cursor.execute("""
                        SELECT session_token 
                        FROM session_tokens 
                        WHERE userID = (SELECT userID FROM Users WHERE username = %s)
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """, (username,))
                    user_session = await cursor.fetchone()

                    if not user_session or not bcrypt.checkpw(session_token.encode("utf-8"), user_session["session_token"].encode("utf-8")):
                        await ws.send(json.dumps({"error": "Invalid user or session token", "status_code": 400}))
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
                        await cursor.execute("""
                                    SELECT m.messageID, m.message, m.timestamp, u.username AS user
                                    FROM Messages m
                                    JOIN Users u ON m.userID = u.userID
                                    WHERE m.chatID = %s AND m.messageID > %s
                                    ORDER BY m.messageID ASC
                                    LIMIT 200;
                                """, (chat_id, last_msg_id))
                        messages = await cursor.fetchall()
                        if messages:
                            last_msg_id = max(msg["messageID"] for msg in messages)
                            for msg in messages:
                                msg["timestamp"] = msg["timestamp"].isoformat()
                                del msg["messageID"]
                            await ws.send(json.dumps({"messages": messages, "status_code": 200}))
                        else:
                            await ws.send(json.dumps({"error" : "No messages found", "status_code": 404}))

                        await asyncio.sleep(1)
                    await conn.commit()
    except Exception as e:
        print(e)
    finally:
        await ws.close()

async def handler(ws):
    """
    Handle incoming WebSocket connections and data.

    :param ws: WebSocket connection.
    """
    try:
        async for user in ws:
            print("User Connected!")
            try:
                data = json.loads(user)
                required_keys = ("username", "receiver", "session_token")
                if all(data.get(key) for key in required_keys):
                    await main(data, ws)
                else:
                    await ws.send(json.dumps({"error": "Invalid data format", "status_code": 400}))
            except json.JSONDecodeError as e:
                await ws.send(json.dumps({"error": "Malformed JSON", "status_code": 400}))
            except Exception as e:
                print(f"Internal error: {e}")
                await ws.send(json.dumps({"error": "Internal server error", "status_code": 500}))
    except websockets.exceptions.ConnectionClosedOK:
        print("Connection closed normally.")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed with error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        try:
            await ws.close()
        except Exception:
            return
        print("WebSocket connection closed.")

async def ws_start():
    """
    Start the WebSocket server with SSL.
    """
    # Create an SSL context with your certificates
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile='./certifs/fullchain.pem', keyfile='./certifs/privkey.pem')

    # Start the WebSocket server with SSL context
    try:
        async with websockets.serve(handler, "0.0.0.0", 8765, ssl=ssl_context):
            await asyncio.Future()  # Keep the server running indefinitely
    except Exception as e:
        print(e)

if __name__ == "__main__":
    asyncio.run(ws_start())
