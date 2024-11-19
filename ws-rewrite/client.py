import asyncio
import websockets


async def send_request():
    uri = "ws://localhost:6420/connection"  # Specify the route you want to connect to
    async with websockets.connect(uri) as websocket:
        # Send a message to the server
        await websocket.send("Hello, server!")

        # Wait for a response
        response = await websocket.recv()
        print(f"Server response: {response}")


if __name__ == "__main__":
    asyncio.run(send_request())
