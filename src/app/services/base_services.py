from app.database.db_helper import fetch_records, insert_record
from flask import jsonify
import bcrypt
import mysql.connector
from flask import request, render_template, redirect, flash, url_for



import bcrypt
import logging

def verif_user(username: str, session_token: str) -> bool:
    """
    Verifies that the given username’s most recent session token matches.
    """
    # Fetch at most one record (the latest) for this user
    cursor = fetch_records(
        table="session_tokens",
        where_clause=(
            "userID = ("
            "SELECT userID FROM users WHERE username = %s"
            ")"
        ),
        params=(username,),
        order_by="created_at DESC",
        limit=1,
        fetch_all=False     # return the raw cursor so we can do .fetchone()
    )

    try:
        row = cursor.fetchone()
    except Exception as e:
        logging.error(f"[verif_user] failed to fetch session token for {username}: {e}")
        return False

    if not row:
        return False  # no such user or no tokens at all

    stored_hash = row["session_token"]
    # Compare the provided token against the stored bcrypt hash
    try:
        return bcrypt.checkpw(session_token.encode("utf-8"),
                              stored_hash.encode("utf-8"))
    except ValueError as e:
        logging.error(f"[verif_user] bcrypt error for user {username}: {e}")
        return False

def return_statement(response=None, error="", status_code=200, additional=None):
    return jsonify({
        "response": response,
        "error": error,
        **(dict([additional]) if additional else {}),
    }), status_code

def index():
    return render_template("welcome.html")

import traceback  # Add this for detailed error logging

def subscribe():
    if request.method == "POST":
        email = request.form.get("email")

        if not email:
            flash("Email is required!", "error")
            return redirect(url_for("subscribe"))

        try:
            # Use fetch_records to check if the email already exists
            existing_emails = fetch_records(
                table="email_subscribers",
                where_clause="email = %s",
                params=(email,),
                fetch_all=True
            )
            if existing_emails:
                flash("This email is already subscribed!", "warning")
                return redirect(url_for("subscribe"))

            # Use insert_record to add the new email
            insert_record("email_subscribers", {"email": email})
            flash("You have successfully subscribed!", "success")
        except mysql.connector.Error as err:
            flash(f"Database error: {err}", "error")
            print(f"Database error: {err}")
            traceback.print_exc()
        except Exception as e:
            flash(f"An unexpected error occurred: {e}", "error")
            print(f"Unexpected error: {e}")
            traceback.print_exc()
    else:
        return render_template("subscribe.html")

    return render_template("subscribe.html")

def verify_connection():
    """
    Test route to verify server is reachable.
    """
    # Handle POST request
    if request.method == "GET":
        return return_statement("", "Incompatible client version!", 400)
    
    elif request.method == "POST":
        # Ensure the JSON body exists
        client_data = request.get_json()
        if not client_data:
            return return_statement("", "Invalid request!", 400)

        version = client_data.get("version")
        if version == "electron_app":
            return return_statement(response="Hello World!")
        else:
            return return_statement("", "Incompatible client version!", 400)
        
    # Fallback (should not be reached)
    return return_statement("", "Unsupported HTTP method!", 405)