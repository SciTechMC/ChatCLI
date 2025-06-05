from app.database.db_helper import get_db
from flask import jsonify
import bcrypt
import mysql.connector
from flask import request, render_template, redirect, flash, url_for



def verif_user(username, session_token):
    """
    Verifies if the user and session token match.
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
    SELECT session_token 
    FROM session_tokens 
    WHERE userID = (SELECT userID FROM Users WHERE username = %s)
    ORDER BY created_at DESC 
    LIMIT 1;
    """, (username,))
    user = cursor.fetchone()
    cursor.close()
    if not user:
        return False  # No user or token found

    # Check if the provided session token matches the stored hash
    return bcrypt.checkpw(session_token.encode("utf-8"), user["session_token"].encode("utf-8"))

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

        conn = get_db()
        cursor = conn.cursor()
        try:
            # Check if the email already exists
            cursor.execute("SELECT email FROM email_subscribers WHERE email = %s", (email,))
            existing_email = cursor.fetchone()
            if existing_email:
                flash("This email is already subscribed!", "warning")
                return redirect(url_for("subscribe"))

            # Insert the new email into the database
            cursor.execute("INSERT INTO email_subscribers (email) VALUES (%s)", (email,))
            conn.commit()
            flash("You have successfully subscribed!", "success")
        except mysql.connector.Error as err:
            flash(f"Database error: {err}", "error")
            print(f"Database error: {err}")  # Print the error to the console
            traceback.print_exc()  # Print the full stack trace
        except Exception as e:
            flash(f"An unexpected error occurred: {e}", "error")
            print(f"Unexpected error: {e}")  # Print the error to the console
            traceback.print_exc()
        finally:
            cursor.close()
            conn.close()
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