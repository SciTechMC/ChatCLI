# app/services/user_services.py

import random
import string
import re
import bcrypt
from datetime import datetime, timedelta

from flask import request, jsonify, render_template, current_app
from app.services.base_services import return_statement
from app.services.mail_services import send_verification_email, send_password_reset_email
from app.database.db_helper import fetch_records, insert_record, update_records


def register():
    """
    Registers a new user and sends a verification code.
    """
    data     = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password")
    email    = (data.get("email") or "").strip()

    # 400: missing/invalid input
    if not username or not password:
        return return_statement("", "Username and password are required", 400)
    if any(ch in r'"%\'()*+,/:;<=>?@[\]^{|}~` ' for ch in username):
        return return_statement("", "Username includes invalid characters", 400)
    if not email:
        return return_statement("", "Email is required", 400)
    if not re.match(r'^[\w\.\+-]+@[\w-]+\.[\w\.-]+$', email):
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

    try:
        # hash password
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        # check existing user
        users = fetch_records(
            table="users",
            where_clause="username = %s",
            params=(username,),
            fetch_all=True
        )

        if users:
            user = users[0]
            if user["email_verified"]:
                return return_statement("", f"User '{username}' already exists", 400)
            user_id = user["userID"]
            # update unverified user
            update_records(
                table="users",
                data={"password": hashed, "email": email, "created_at": datetime.utcnow()},
                where_clause="userID = %s",
                where_params=(user_id,)
            )
            # revoke any recent tokens
            update_records(
                table="email_tokens",
                data={"revoked": True},
                where_clause="userID = %s AND expires_at > %s",
                where_params=(user_id, datetime.utcnow())
            )
        else:
            # insert new user
            user_id = insert_record(
                "users",
                {
                    "username": username,
                    "password": hashed,
                    "email": email,
                    "email_verified": False
                }
            )

        # create verification token
        email_token = f"{random.randint(100000, 999999)}"
        expiry      = datetime.utcnow() + timedelta(minutes=5)
        insert_record(
            "email_tokens",
            {
                "userID":      user_id,
                "email_token": email_token,
                "expires_at":  expiry,
                "revoked":     False
            }
        )

    except Exception:
        current_app.logger.exception("Error during user registration")
        return return_statement("", "Internal server error", 500)

    # send code
    if not send_verification_email(username, email_token, email):
        return return_statement("", "Failed to send verification email", 500)

    return return_statement("Verification email sent!")


def verify_email():
    """
    Consumes a verification token and marks the user verified.
    """
    data        = request.get_json(silent=True) or {}
    username    = (data.get("username") or "").strip().lower()
    client_code = data.get("email_token")

    if not username or not client_code:
        return return_statement("", "Username and email_token are required", 400)

    try:
        # fetch the latest valid token
        cursor = fetch_records(
            table="email_tokens",
            where_clause=(
                "userID = (SELECT userID FROM users WHERE username = %s) "
                "AND revoked = FALSE AND expires_at > %s"
            ),
            params=(username, datetime.utcnow()),
            order_by="created_at DESC",
            limit=1,
            fetch_all=False
        )
        row = cursor.fetchone()
        if not row or str(row["email_token"]) != str(client_code):
            return return_statement("", "Invalid or expired code!", 400)

        # mark token revoked
        update_records(
            table="email_tokens",
            data={"revoked": True},
            where_clause="tokenID = %s",
            where_params=(row["tokenID"],)
        )
        # mark user verified
        update_records(
            table="users",
            data={"email_verified": True},
            where_clause="userID = %s",
            where_params=(row["userID"],)
        )
        return return_statement("Email verified!")

    except Exception:
        current_app.logger.exception("Error during email verification")
        return return_statement("", "Internal server error", 500)


def login():
    """
    Authenticates credentials and issues a session token.
    """
    data     = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password")

    if not username or not password:
        return return_statement("", "Username and password required", 400)

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

        # issue session token
        token_plain = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
        token_hash  = bcrypt.hashpw(token_plain.encode("utf-8"), bcrypt.gensalt())
        expiry      = datetime.utcnow() + timedelta(days=7)  # adjust if needed

        insert_record(
            "session_tokens",
            {
                "userID":        user["userID"],
                "session_token": token_hash,
                "expires_at":    expiry,
                "revoked":       False,
                "ip_address":    request.remote_addr
            }
        )

        return return_statement(
            "", 
            "Login successful",
            200,
            additional=["session_token", token_plain]
        )

    except Exception:
        current_app.logger.exception("Error during login")
        return return_statement("", "Internal server error", 500)


def reset_password_request():
    """
    Generates a reset token and emails a reset link.
    """
    data       = request.get_json(silent=True) or {}
    identifier = (data.get("data") or "").strip()
    if not identifier:
        return return_statement("", "Invalid input", 400)

    try:
        # find user by email or username
        if re.match(r'^[^@]+@[^@]+\.[^@]+$', identifier):
            users = fetch_records("users", "email = %s", (identifier,), fetch_all=True)
        else:
            users = fetch_records("users", "username = %s", (identifier,), fetch_all=True)

        if not users:
            return return_statement("", "User not found", 404)

        user      = users[0]
        username  = user["username"]
        email     = user["email"]
        user_id   = user["userID"]
        reset_tok = 't0k3n' + ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        expiry    = datetime.utcnow() + timedelta(hours=1)

        insert_record(
            "pass_reset_tokens",
            {
                "userID":      user_id,
                "reset_token": reset_tok,
                "expires_at":  expiry,
                "revoked":     False
            }
        )

    except Exception:
        current_app.logger.exception("Error during password-reset request")
        return return_statement("", "Internal server error", 500)

    if not send_password_reset_email(username, reset_tok, email):
        return return_statement("", "Failed to send password reset email", 500)

    return return_statement("Password reset email sent!")


def reset_password():
    """
    Renders form (GET) or applies new password (POST), revoking the reset token.
    """
    token    = request.args.get('token')
    username = request.args.get('username')

    if request.method == 'POST':
        password = request.form.get('password')
        confirm  = request.form.get('confirm_password')

        if not (username and token):
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
            # verify reset token
            cursor = fetch_records(
                table="pass_reset_tokens",
                where_clause="reset_token = %s AND revoked = FALSE AND expires_at > %s",
                params=(token, datetime.utcnow()),
                order_by="created_at DESC",
                limit=1,
                fetch_all=False
            )
            row = cursor.fetchone()
            if not row:
                return jsonify({"error": "Invalid or expired reset link"}), 400

            # update password
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            update_records(
                table="users",
                data={"password": hashed},
                where_clause="userID = %s",
                where_params=(row["userID"],)
            )
            # revoke token
            update_records(
                table="pass_reset_tokens",
                data={"revoked": True},
                where_clause="tokenID = %s",
                where_params=(row["tokenID"],)
            )

            return jsonify({"message": "Password reset successfully"}), 200

        except Exception:
            current_app.logger.exception("Error during password reset")
            return jsonify({"error": "Internal server error"}), 500

    # GET: show reset form
    return render_template("reset_password.html", username=username, token=token)