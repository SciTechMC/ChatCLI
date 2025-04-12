from flask import Flask
from chatcli.app.routes import all_blueprints

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secret!'

    # Register blueprints
    for bp in all_blueprints:
        app.register_blueprint(bp)

    return app