from flask import Blueprint, current_app, jsonify, request
import app.services.chat_services as chat_services
from app.extensions  import limiter

chat = Blueprint("chat", __name__, url_prefix="/chat")

@chat.route("/")
def index():
    return "chat's index route"

@chat.route("/fetch-chats", methods=["POST"])
def route_fetch_chats():
    try:
        return chat_services.fetch_chats()
    except Exception as e:
        current_app.logger.error("Unhandled exception in fetch_chats", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@chat.route("/create-chat", methods=["POST"])
def route_create_chat():
    try:
        return chat_services.create_chat()
    except Exception as e:
        current_app.logger.error("Unhandled exception in create_chat", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@chat.route("/create-group", methods=["POST"])
def route_create_group():
    try:
        return chat_services.create_group()
    except Exception as e:
        current_app.logger.error("Unhandled exception in create_group", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@chat.route("/add-members", methods=["POST"])
def route_add_members():
    try:
        return chat_services.add_participant()
    except Exception as e:
        current_app.logger.error("Unhandled exception in add_participant", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@chat.route("/remove-members", methods=["POST"])
def route_remove_members():
    try:
        return chat_services.remove_participant()
    except Exception as e:
        current_app.logger.error("Unhandled exception in remove_participant", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@chat.route("/messages", methods=["POST"])
def route_messages():
    try:
        return chat_services.get_messages()
    except Exception as e:
        current_app.logger.error("Unhandled exception in get_messages", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@chat.route("/archive-chat", methods=["POST"])
@limiter.limit("10 per minute")
def route_archive_chat():
    try:
        return chat_services.archive_chat()
    except Exception as e:
        current_app.logger.error("Unhandled exception in archive_chat", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@chat.route("/get-members", methods=["POST"])
def route_get_members():
    try:
        return chat_services.get_members()
    except Exception as e:
        current_app.logger.error("Unhandled exception in get_members", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    
@chat.route("/fetch-archived", methods=["POST"])
def route_fetch_archived():
    """
    Fetch archived chats
    """
    try:
        return chat_services.fetch_archived()
    except Exception as e:
        current_app.logger.error("Unhandled exception in fetch_archived", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@chat.route("/unarchive-chat", methods=["POST"])
@limiter.limit("10 per minute")
def route_unarchive_chat():
    """
    Unarchive a chat
    """
    try:
        return chat_services.unarchive_chat()
    except Exception as e:
        current_app.logger.error("Unhandled exception in unarchive_chat", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500