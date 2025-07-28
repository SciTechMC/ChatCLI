from flask import Blueprint, request, jsonify
from app.services.chat_services import (
    fetch_chats,
    create_chat,
    create_group,
    add_participant,
    remove_participant,
    get_messages,
    archive_chat,
    get_members,
    fetch_archived,
    unarchive_chat,
)
from app.errors import BadRequest
from app.extensions import limiter

chat = Blueprint("chat", __name__, url_prefix="/chat")

@chat.route("/")
def index():
    return "chat's index route"

@chat.route("/fetch-chats", methods=["POST"])
def route_fetch_chats():
    data = request.get_json(silent=True)
    if not data:
        raise BadRequest("Invalid JSON format.")
    result = fetch_chats(data)
    return jsonify(result)

@chat.route("/create-chat", methods=["POST"])
def route_create_chat():
    data = request.get_json(silent=True)
    if not data:
        raise BadRequest("Invalid JSON format.")
    result = create_chat(data)
    return jsonify(result), 201

@chat.route("/create-group", methods=["POST"])
def route_create_group():
    data = request.get_json(silent=True)
    if not data:
        raise BadRequest("Invalid JSON format.")
    result = create_group(data)
    return jsonify(result), 201

@chat.route("/add-members", methods=["POST"])
def route_add_members():
    data = request.get_json(silent=True)
    if not data:
        raise BadRequest("Invalid JSON format.")
    result = add_participant(data)
    return jsonify(result)

@chat.route("/remove-members", methods=["POST"])
def route_remove_members():
    data = request.get_json(silent=True)
    if not data:
        raise BadRequest("Invalid JSON format.")
    result = remove_participant(data)
    return jsonify(result)

@chat.route("/messages", methods=["POST"])
def route_messages():
    data = request.get_json(silent=True)
    if not data:
        raise BadRequest("Invalid JSON format.")
    result = get_messages(data)
    return jsonify(result)

@chat.route("/archive-chat", methods=["POST"])
@limiter.limit("10 per minute")
def route_archive_chat():
    data = request.get_json(silent=True)
    if not data:
        raise BadRequest("Invalid JSON format.")
    result = archive_chat(data)
    return jsonify(result)

@chat.route("/get-members", methods=["POST"])
def route_get_members():
    data = request.get_json(silent=True)
    if not data:
        raise BadRequest("Invalid JSON format.")
    result = get_members(data)
    return jsonify(result)

@chat.route("/fetch-archived", methods=["POST"])
def route_fetch_archived():
    data = request.get_json(silent=True)
    if not data:
        raise BadRequest("Invalid JSON format.")
    result = fetch_archived(data)
    return jsonify(result)

@chat.route("/unarchive-chat", methods=["POST"])
@limiter.limit("10 per minute")
def route_unarchive_chat():
    data = request.get_json(silent=True)
    if not data:
        raise BadRequest("Invalid JSON format.")
    result = unarchive_chat(data)
    return jsonify(result)