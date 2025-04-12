from flask import Blueprint
from chatcli.app.services.chat_services import fetch_chats,create_chat,receive_message

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

@chat.route("/receive-message", methods=["POST"])
def route_receive_message():
    return receive_message()