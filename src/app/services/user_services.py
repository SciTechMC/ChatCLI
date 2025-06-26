from flask import request, jsonify, render_template
from app.services.base_services import return_statement, verif_user
from app.services.mail_services import send_verification_email, send_password_reset_email
from app.database.db_helper import fetch_records, insert_record, update_records
import random
import string
import bcrypt
import re
from datetime import datetime

def register():
    """
    Registers a new user in the system.
    """
    client   = request.get_json() or {}
    username = (client.get("username") or "").lower()
    password = client.get("password")
    email    = client.get("email")

    # Validate input fields
    if not username or not password:
        return return_statement("", "Username and password are required", 400)
    if any(ch in r'"%\'()*+,/:;<=>?@[\]^{|}~` ' for ch in username):
        return return_statement("", "Username includes bad characters", 400)
    if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
        return return_statement("", "Invalid email address", 400)
    if (
        len(password) < 8 or
        not any(ch.isupper() for ch in password) or
        not any(ch.islower() for ch in password) or
        not any(ch.isdigit() for ch in password) or
        not any(ch in string.punctuation for ch in password)
    ):
        return return_statement(
            "", 
            "Password must be ≥8 chars, include upper, lower, digit & special",
            400
        )

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    try:
        # see if user exists
        existing = fetch_records(
            table="users",
            where_clause="username = %s",
            params=(username,),
            fetch_all=True
        )
        if existing:
            user = existing[0]
            if user["email_verified"]:
                return return_statement("", f"User '{username}' already exists", 400)

            # update unverified user
            update_records(
                table="users",
                data={
                    "username": username,
                    "password": hashed,
                    "email": email,
                    "created_at": datetime.now()
                },
                where_clause="userID = %s",
                where_params=(user["userID"],)
            )
            # disable any recent tokens
            update_records(
                table="email_tokens",
                data={"revoked": True},
                where_clause="NOW() <= DATE_ADD(created_at, INTERVAL 6 MINUTE) AND userID = %s",
                where_params=(user["userID"],)
            )
            user_id = user["userID"]
        else:
            # create new user
            user_id = insert_record(
                "users",
                {
                    "username": username,
                    "password": hashed,
                    "email": email,
                    "email_verified": False
                }
            )

        # generate & store verification code
        email_token = str(random.randint(100000, 999999))
        insert_record(
            "email_tokens",
            {"userID": user_id, "email_token": email_token}
        )
    except Exception as e:
        return return_statement("", str(e), 500)

    # send the code via centralized mail service
    if not send_verification_email(username, email_token, email):
        return return_statement("", "Failed to send verification email", 500)
    return return_statement("Email sent successfully!")


def verify_email():
    client_code = request.get_json().get("email_token")
    username    = request.get_json().get("username", "").lower()

    if not username or not client_code:
        return return_statement("", "username and email_token are required", 400)

    try:
        # fetch latest valid token
        cur = fetch_records(
            table="email_tokens",
            where_clause=(
                "userID = (SELECT userID FROM users WHERE username = %s) "
                "AND NOW() <= DATE_ADD(created_at, INTERVAL 5 MINUTE) "
                "AND revoked = FALSE"
            ),
            params=(username,),
            order_by="created_at DESC",
            limit=1,
            fetch_all=False
        )
        row = cur.fetchone()
        if not row or str(row["email_token"]) != str(client_code):
            return return_statement("", "Invalid code!", 400)

        update_records(
            table="users",
            data={"email_verified": True},
            where_clause="username = %s",
            where_params=(username,)
        )
        return return_statement("Email verified!")
    except Exception as e:
        return return_statement("", str(e), 500)


def login():
    """
    Logs in a user and issues a session token.
    """
    client   = request.get_json() or {}
    username = (client.get("username") or "").lower()
    password = client.get("password")

    if not username or not password:
        return return_statement("", "username and password required", 400)

    try:
        users = fetch_records(
            table="users",
            where_clause="username = %s",
            params=(username,),
            fetch_all=True
        )
        if not users:
            return return_statement("", "Username not found!", 404)

        user = users[0]
        if not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
            return return_statement("", "Invalid password", 400)

        # generate session token
        token_plain = ''.join(random.choices(string.ascii_uppercase + string.digits, k=64))
        token_hash  = bcrypt.hashpw(token_plain.encode("utf-8"), bcrypt.gensalt())

        insert_record(
            "session_tokens",
            {
                "userID": user["userID"],
                "session_token": token_hash,
                "ip_address": request.remote_addr,
                "is_active": True
            }
        )
        return return_statement("Login successful!", additional=["session_token", token_plain])
    except Exception as e:
        return return_statement("", str(e), 500)


def reset_password_request():
    """
    Sends a password reset email to the user.
    """
    data       = request.get_json() or {}
    identifier = data.get("data")
    if not identifier:
        return return_statement("", "Invalid input", 400)

    try:
        # look up by email or username
        if re.match(r'^[^@]+@[^@]+\.[^@]+$', identifier):
            users = fetch_records("users", "email = %s", (identifier,), fetch_all=True)
        else:
            users = fetch_records("users", "username = %s", (identifier,), fetch_all=True)
        if not users:
            return return_statement("", "User not found", 404)

        user    = users[0]
        username, email, user_id = user["username"], user["email"], user["userID"]

        # create reset token
        token = 't0k3n' + ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        insert_record(
            "pass_reset_tokens",
            {"userID": user_id, "reset_token": token}
        )
    except Exception as e:
        return return_statement("", str(e), 500)

    # send reset link
    if not send_password_reset_email(username, token, email):
        return return_statement("", "Failed to send password reset email", 500)
    return return_statement("Email sent successfully!")


def reset_password():
    """
    Renders or handles the password-reset form.
    """
    token    = request.args.get('token')
    username = request.args.get('username')

    if request.method == 'POST':
        password = request.form.get('password')
        confirm  = request.form.get('confirm_password')
        if not username or not token:
            return jsonify({"error": "Missing username or token"}), 400
        if password != confirm:
            return jsonify({"error": "Passwords do not match"}), 400
        if (
            len(password) < 8 or
            not any(ch.isupper() for ch in password) or
            not any(ch.islower() for ch in password) or
            not any(ch.isdigit() for ch in password) or
            not any(ch in string.punctuation for ch in password)
        ):
            return jsonify({"error": "Password must be ≥8 chars, include upper, lower, digit & special"}), 400

        try:
            users = fetch_records("users", "username = %s", (username,), fetch_all=True)
            if not users:
                return jsonify({"error": f"User does not exist: {username}"}), 404

            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            update_records(
                "users",
                {"password": hashed},
                where_clause="userID = %s",
                where_params=(users[0]["userID"],)
            )
            return jsonify({"message": "Password reset successfully"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # GET: render the form
    return render_template("reset_password.html", username=username, token=token)