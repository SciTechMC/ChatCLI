from app.database.db_helper import fetch_records, insert_record
from flask import jsonify, request, render_template, redirect, flash, url_for
import mysql.connector
import hashlib
import os
import logging

# module logger
tmp_logger = logging.getLogger(__name__)

def authenticate_token(session_token: str) -> str | None:
    """
    Given a plain session token, find the single matching row in session_tokens
    (hashed with SHA-256), where revoked = FALSE and expires_at > NOW().
    If found and the user is verified, return their username; otherwise None.
    """
    try:
        # 1) Hash the incoming token
        token_hash = hashlib.sha256(session_token.encode("utf-8")).hexdigest()

        # 2) Targeted lookup in session_tokens
        sessions = fetch_records(
            table="session_tokens",
            where_clause="session_token = %s AND revoked = FALSE AND expires_at > CURRENT_TIMESTAMP()",
            params=(token_hash,),
            fetch_all=True
        )
        if not sessions:
            return None

        user_id = sessions[0]["userID"]

        # 3) Make sure the user exists, is verified (and not disabled if you want)
        users = fetch_records(
            table="users",
            where_clause="userID = %s AND email_verified = TRUE AND disabled = FALSE",
            params=(user_id,),
            fetch_all=True
        )
        if not users:
            return None

        return users[0]["username"]

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