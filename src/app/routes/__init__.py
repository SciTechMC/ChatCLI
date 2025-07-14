from flask import Blueprint
from app.routes.user_routes import user
from app.routes.chat_routes import chat
from app.routes.base_routes import base

all_blueprints = [user, chat, base]