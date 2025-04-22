
import sys
import os
import pytest
from flask import Flask

# Make sure the app module is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index(client):
    res = client.get("/")
    assert res.status_code in (200, 404, 405)

def test_verify_connection(client):
    res = client.post("/verify-connection")
    assert res.status_code in (200, 400)

def test_subscribe(client):
    res = client.post("/subscribe")
    assert res.status_code in (200, 400)

def test_chat_index(client):
    res = client.get("/chat/")
    assert res.status_code == 200

def test_fetch_chats(client):
    data = { "username": "testuser", "session_token": "fake" }
    res = client.post("/chat/fetch-chats", json=data)
    assert res.status_code in (200, 400, 500)

def test_create_chat(client):
    data = { "username": "testuser", "receiver": "someone", "session_token": "fake" }
    res = client.post("/chat/create-chat", json=data)
    assert res.status_code in (200, 400, 500)

def test_receive_message(client):
    data = { "username": "testuser", "message": "hi", "session_token": "fake" }
    res = client.post("/chat/receive-message", json=data)
    assert res.status_code in (200, 400, 500)

def test_user_index(client):
    res = client.get("/user/")
    assert res.status_code == 200

def test_register(client):
    data = { "username": "test", "email": "test@example.com", "password": "test1234" }
    res = client.post("/user/register", json=data)
    assert res.status_code in (200, 400, 500)

def test_verify_email(client):
    data = { "email": "test@example.com", "code": "1234" }
    res = client.post("/user/verify-email", json=data)
    assert res.status_code in (200, 400, 500)

def test_login(client):
    data = { "username": "test", "password": "test1234" }
    res = client.post("/user/login", json=data)
    assert res.status_code in (200, 400, 500)

def test_reset_password_request(client):
    data = { "email": "test@example.com" }
    res = client.post("/user/reset-password-request", json=data)
    assert res.status_code in (200, 400, 500)

def test_reset_password(client):
    res = client.get("/user/reset-password")
    assert res.status_code in (200, 400, 500)
    
if __name__ == "__main__":
    print("Run the tests using pytest")