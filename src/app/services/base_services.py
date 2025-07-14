from app.database.db_helper import fetch_records, insert_record
from flask import jsonify, request, render_template, redirect, flash, url_for
import mysql.connector
from datetime import datetime, timezone
import hashlib
import os
import logging

# module logger
tmp_logger = logging.getLogger(__name__)


def authenticate_token(session_token: str) -> str | None:
    """
    Given a plain session token, find the matching unrevoked, unexpired
    row in `session_tokens` (hashed with SHA-256), then return its username.
    Otherwise return None.
    """
    try:
        token_hash = hashlib.sha256(session_token.encode("utf-8")).hexdigest()
        sessions = fetch_records(
            table="session_tokens",
            where_clause="revoked = FALSE AND expires_at > %s",
            params=(datetime.now(timezone.utc),),
            fetch_all=True
        )
        # Find matching session
        match = next((s for s in sessions if s.get("session_token") == token_hash), None)
        if not match:
            return None

        users = fetch_records(
            table="users",
            where_clause="userID = %s AND email_verified = TRUE",
            params=(match.get("userID"),),
            fetch_all=True
        )
        if not users or not isinstance(users, list):
            return None

        # Safely extract username
        username = users[0].get("username")
        return username

    except Exception as e:
        tmp_logger.error("Error authenticating token: %s", e, exc_info=e)
        return None


def return_statement(response, message="", status: int=200, additional: dict=None):
    """
    Consistent JSON response formatter. Always safe-bounds user data.
    """
    payload = {
        "status": "ok" if status == 200 else "error",
        "message": message,
        "response": response
    }
    if additional and isinstance(additional, dict):
        payload.update(additional)
    return jsonify(payload), status


def index():
    """
    Render welcome page.
    """
    try:
        return render_template("welcome.html")
    except Exception as e:
        tmp_logger.error("Error rendering index: %s", e, exc_info=e)
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

def subscribe():
    if request.method == "POST":
        email = request.form.get("email")

        if not email:
            flash("Email is required!", "error")
            return redirect(url_for("subscribe"))

        try:
            existing_emails = fetch_records(
                table="email_subscribers",
                where_clause="email = %s",
                params=(email,),
                fetch_all=True
            )
            if existing_emails:
                flash("This email is already subscribed!", "warning")
                return redirect(url_for("subscribe"))

            insert_record("email_subscribers", {"email": email})
            flash("You have successfully subscribed!", "success")
        except mysql.connector.Error as err:
            flash(f"Database error: {err}", "error")
            if os.getenv("FLASK_ENV") == "development":
                print(f"Failed to subscribe email {email}: {err}")
            else:
                tmp_logger.error("Failed to subscribe email %s: %s", email, err)
        except Exception as e:
            flash(f"An unexpected error occurred: {e}", "error")
            if os.getenv("FLASK_ENV") == "development":
                print(f"Unexpected error: {e}")
            else:
                tmp_logger.error("Unexpected error during subscription: %s", e)
    else:
        return render_template("subscribe.html")

    return render_template("subscribe.html")


def verify_connection():
    """
    Test route to verify server is reachable.
    """
    return return_statement(response="Server is reachable!")