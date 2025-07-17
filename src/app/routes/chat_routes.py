from flask import Blueprint, current_app, jsonify, request
from app.services.chat_services import (
    fetch_chats,
    create_chat,         # private‐chat creator
    get_messages,
    archive_chat,
    create_group,        # group‐chat creator
    add_participant,     # add to group
    remove_participant,   # remove from group
    get_members,
    fetch_archived,  # fetch archived chats
    unarchive_chat  # unarchive a chat
)

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
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@chat.route("/create-chat", methods=["POST"])
def route_create_chat():
    try:
        return create_chat()
    except Exception as e:
        current_app.logger.error("Unhandled exception in create_chat", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@chat.route("/create-group", methods=["POST"])
def route_create_group():
    """
    POST JSON:
      {
        "session_token": "...",
        "name":          "My Group Name",
        "members":      ["alice", "bob", "charlie"]
      }
    """
    try:
        return create_group()
    except Exception as e:
        current_app.logger.error("Unhandled exception in create_group", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@chat.route("/add-members", methods=["POST"])
def route_add_members():
    """
    POST JSON:
      {
        "session_token": "...",
        "chatID":        123,
        "members":      ["dave", "eve"]
      }
    """
    try:
        return add_participant()
    except Exception as e:
        current_app.logger.error("Unhandled exception in add_participant", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@chat.route("/remove-members", methods=["POST"])
def route_remove_members():
    """
    POST JSON:
      {
        "session_token": "...",
        "chatID":        123,
        "members":      ["bob"]
      }
    """
    try:
        return remove_participant()
    except Exception as e:
        current_app.logger.error("Unhandled exception in remove_participant", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@chat.route("/messages", methods=["POST"])
def route_messages():
    try:
        return get_messages()
    except Exception as e:
        current_app.logger.error("Unhandled exception in get_messages", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@chat.route("/archive-chat", methods=["POST"])
def route_archive_chat():
    try:
        return archive_chat()
    except Exception as e:
        current_app.logger.error("Unhandled exception in archive_chat", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@chat.route("/get-members", methods=["POST"])
def route_get_members():
    try:
        return get_members()
    except Exception as e:
        current_app.logger.error("Unhandled exception in get_members", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    
@chat.route("/fetch-archived", methods=["POST"])
def route_fetch_archived():
    """
    Fetch archived chats
    """
    try:
        return fetch_archived()
    except Exception as e:
        current_app.logger.error("Unhandled exception in fetch_archived", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@chat.route("/unarchive-chat", methods=["POST"])
def route_unarchive_chat():
    """
    Unarchive a chat
    """
    try:
        return unarchive_chat()
    except Exception as e:
        current_app.logger.error("Unhandled exception in unarchive_chat", exc_info=e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500