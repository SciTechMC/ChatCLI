import asyncio
import websockets
import json

client_version = "pre-alpha V0.3.0"

async def send_request():
    uri = "ws://localhost:6420/"  # Specify the route you want to connect to
    async with websockets.connect(uri) as websocket:
        # Send a message to the server
        await websocket.send(json.dumps({"path" : "connection", "client_version" : client_version}))

        # Wait for a response
        response = await websocket.recv()
        response = json.loads(response)
        print(f"Server response: {str(response)}")


if __name__ == "__main__":
    asyncio.run(send_request())
