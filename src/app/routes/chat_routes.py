from flask import Blueprint
from app.services.chat_services import fetch_chats,create_chat, get_messages, delete_chat

chat = Blueprint("chat", __name__, url_prefix="/chat")

@chat.route("/")
def index():
    return "chat's index route"

@chat.route("/fetch-chats", methods=["POST"])
def route_fetch_chats():
    return fetch_chats()

@chat.route("/create-chat", methods=["POST"])
def route_create_chat():
    return create_chat()

@chat.route("/messages", methods=["POST"])
def route_messages():
    return get_messages()

@chat.route("/delete-chat", methods=["POST"])
def route_delete_chat():
    return delete_chat()