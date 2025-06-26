from flask import Flask
from app.routes.user_routes import user
from app.routes.chat_routes import chat
from app.routes.base_routes import base
import os

all_blueprints = [user, chat, base]

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY")

    # Register blueprints
    for bp in all_blueprints:
        app.register_blueprint(bp)

    return app