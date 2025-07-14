from flask import Blueprint
from app.services.user_services import register, verify_email, login, reset_password, reset_password_request, refresh_token

user = Blueprint("user", __name__, url_prefix="/user")

@user.route("/")
def route_index():
    return "User's index route"

@user.route("/register", methods=["POST"])
def route_register():
    return register()

@user.route("/verify-email", methods=["POST"])
def route_verify_email():
    return verify_email()

@user.route("/login", methods=["POST"])
def route_login():
    return login()

@user.route("/reset-password-request", methods=["POST"])
def route_reset_password_request():
    return reset_password_request()

@user.route("/reset-password", methods=["GET", "POST"])
def route_reset_password():
    return reset_password()

user.route("/refresh-token")
def route_refresh_token():
    return refresh_token()
