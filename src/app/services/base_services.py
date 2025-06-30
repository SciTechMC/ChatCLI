from app.database.db_helper import fetch_records, insert_record
from flask import jsonify
import bcrypt
import mysql.connector
from flask import request, render_template, redirect, flash, url_for



import bcrypt
import logging

def authenticate_token(session_token: str) -> bool:
    """
    Given a plain session token, find the matching unrevoked, unexpired
    row in `session_tokens`, then return its username. Otherwise return None.
    """
    # 1) Grab all live sessions
    rows = fetch_records(
        table="session_tokens",
        where_clause="revoked = FALSE AND expires_at > CURRENT_TIMESTAMP()",
        fetch_all=True
    )

    # 2) Find the one whose bcrypt hash matches
    match = None
    for r in rows:
        try:
            if bcrypt.checkpw(
                session_token.encode("utf-8"),
                r["session_token"].encode("utf-8")
            ):
                match = r
                break
        except ValueError:
            continue

    if not match:
        return None

    # 3) Lookup that session’s username
    users = fetch_records(
        table="users",
        where_clause="userID = %s AND email_verified = TRUE",
        params=(match["userID"],),
        fetch_all=True
    )
    if not users:
        return None

    return users[0]["username"]

def return_statement(response, message="", status=200, additional=None):
    return jsonify({
        "status": "ok" if status == 200 else "error",
        "message": message,
        "response": response,
        **(additional if additional else {})
    }), status

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
    return return_statement(response="Server is reachable!")
    # Handle POST request
    # if request.method == "GET":
    #     return return_statement("", "Incompatible client version!", 400)
    
    # elif request.method == "POST":
    #     # Ensure the JSON body exists
    #     client_data = request.get_json()
    #     if not client_data:
    #         return return_statement("", "Invalid request!", 400)

    #     version = client_data.get("version")
    #     if version == "electron_app":
    #         return return_statement(response="Hello World!")
    #     else:
    #         return return_statement("", "Incompatible client version!", 400)
        
    # # Fallback (should not be reached)
    # return return_statement("", "Unsupported HTTP