from flask import Blueprint
import app.services.base_services as base_s
from flask import render_template

base = Blueprint("base", __name__)

@base.route("/", methods=["POST", "GET"])
def index():
    return render_template("welcome.html")

@base.route("/verify-connection", methods=["POST", "GET"])
def verif_conn():
    return base_s.verify_connection()

@base.route("/subscribe", methods=["GET", "POST"])
def subscribe():
    return base_s.subscribe()