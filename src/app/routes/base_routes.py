from flask import Blueprint
import app.services.base_services as base_services
from flask import render_template

base = Blueprint("base", __name__)

@base.route("/", methods=["GET"])
def index():
    return render_template("welcome.html")

@base.route("/verify-connection", methods=["POST", "GET"])
def verif_connection():
    return base_services.verify_connection()

@base.route("/subscribe", methods=["GET", "POST"])
def subscribe():
    return base_services.subscribe()