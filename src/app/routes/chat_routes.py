from flask import Blueprint
from app.services.chat_services import fetch_chats, create_chat, get_messages, delete_chat
from flask import current_app, jsonify, request

chat = Blueprint("chat", __name__, url_prefix="/chat")

@chat.route("/")
def index():
    return "chat's index route"

@chat.route("/fetch-chats", methods=["POST"])
def route_fetch_chats():
    try:
        return fetch_chats()
    except Exception as e:
        current_app.logger.error("Unhandled exception in fetch_chats", exc_info=e)
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

@chat.route("/create-chat", methods=["POST"])
def route_create_chat():
    try:
        # service reads request.json itself, so call without args
        return create_chat()
    except Exception as e:
        current_app.logger.error("Unhandled exception in create_chat", exc_info=e)
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

@chat.route("/messages", methods=["POST"])
def route_messages():
    try:
        return get_messages()
    except Exception as e:
        current_app.logger.error("Unhandled exception in get_messages", exc_info=e)
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

@chat.route("/delete-chat", methods=["POST"])
def route_delete_chat():
    try:
        return delete_chat()
    except Exception as e:
        current_app.logger.error("Unhandled exception in delete_chat", exc_info=e)
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500
