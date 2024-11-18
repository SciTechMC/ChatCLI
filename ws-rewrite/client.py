import asyncio, websockets, rich
import requests


async def check_url():
    client_version = "pre-alpha V0.1.0"
    possible_server_urls = [
        "http://fortbow.duckdns.org",
        "http://172.27.27.231",
        "http://127.0.0.1"
    ]
    print("Connecting to the server.")
    for url in possible_server_urls:
        response = requests.post(url + ":5000/connection", json={"client_version" : client_version})
        if response.status_code == 200:
            return url

async def start_client():
    url = str(check_url()) + ":6942"
    async with websockets.connect(url) as ws:
        await ws.send({"init_connection" : "Hello!"})
        print(ws.recv())


if __name__ == "__main__":
    asyncio.run(start_client())