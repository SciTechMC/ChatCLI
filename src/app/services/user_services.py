# app/services/user_services.py
import string
import re
import bcrypt
from datetime import datetime, timedelta, timezone
import secrets
import hashlib
import random
from flask import request, jsonify, render_template, current_app
from app.services.base_services import return_statement, authenticate_token
from app.services.mail_services import send_verification_email, send_password_reset_email
from app.database.db_helper import fetch_records, insert_record, update_records
import os

alphabet = string.ascii_letters + string.digits

def register():
    """
    Registers a new user and sends a verification code.
    """
    data     = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
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

        # check existing user (case-insensitive)
        users = fetch_records(
            table="users",
            where_clause="LOWER(username) = LOWER(%s)",
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
                data={"password": hashed, "email": email, "created_at": datetime.now(timezone.utc)},
                where_clause="userID = %s",
                where_params=(user_id,)
            )
            # revoke any recent tokens
            update_records(
                table="email_tokens",
                data={"revoked": True},
                where_clause="userID = %s AND expires_at > %s",
                where_params=(user_id, datetime.now(timezone.utc))
            )
        else:
            # insert new user (preserve capitalization)
            user_id = insert_record(
                "users",
                {
                    "username": username,
                    "password": hashed,
                    "email": email,
                    "email_verified": False
                }
            )

        # create verification token (6-digit code)
        email_token = f"{random.randint(100000, 999999):06d}"
        expiry      = datetime.now(timezone.utc) + timedelta(minutes=5)
        if os.getenv("FLASK_ENV") == "dev":
            print(f"Dev mode: Verification code for {username} is {email_token}")
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
    client_code = (data.get("email_token") or "").strip()
    

    if not username or not client_code:
        return return_statement("", "Username and email_token are required", 400)

    
    try:
        # fetch the latest valid token
        row = fetch_records(
            table="email_tokens",
            where_clause=(
                "userID = (SELECT userID FROM users WHERE LOWER(username) = LOWER(%s)) "
                "AND revoked = FALSE AND expires_at > %s"
            ),
            params=(username, datetime.now(timezone.utc)),
            order_by="created_at DESC",
            limit=1,
            fetch_all=False
        )
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


def hash_token(token_plain: str) -> str:
    return hashlib.sha256(token_plain.encode("utf-8")).hexdigest()

def login():
    """
    Authenticates credentials and issues an access token + refresh token.
    """
    data     = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password")

    if not username or not password:
        return return_statement("", "Username and password required", 400)

    try:
        users = fetch_records(
            table="users",
            where_clause="username = %s AND email_verified = 1 AND disabled = 0",
            params=(username,),
            fetch_all=True
        )
        if not users:
            return return_statement("", "Username or password is incorrect!", 400)

        user = users[0]
        if not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
            return return_statement("", "Username or password is incorrect!", 400)

        now = datetime.now(timezone.utc)

        # ——— Generate Access Token ———
        access_plain  = secrets.token_urlsafe(48)
        access_hash   = hash_token(access_plain)
        access_expiry = now + timedelta(days=7)

        insert_record(
            "session_tokens",
            {
                "userID":        user["userID"],
                "session_token": access_hash,
                "expires_at":    access_expiry,
                "revoked":       False,
                "ip_address":    request.remote_addr
            }
        )

        # ——— Generate Refresh Token ———
        refresh_plain  = secrets.token_urlsafe(64)
        refresh_hash   = hash_token(refresh_plain)
        refresh_expiry = now + timedelta(days=30)

        insert_record(
            "refresh_tokens",
            {
                "user_id":    user["userID"],
                "token":      refresh_hash,
                "expires_at": refresh_expiry,
                "revoked":    False
            }
        )

        # ——— Return both tokens to client ———
        return return_statement(
            "", 
            "Login successful",
            200,
            additional={
              "access_token":  access_plain,
              "refresh_token": refresh_plain
            }
        )

    except Exception:
        current_app.logger.exception("Error during login")
        return return_statement("", "Internal server error", 500)

def refresh_token():
    """
    Rotates a valid refresh token and issues a new access token + refresh token.
    """
    data          = request.get_json(silent=True) or {}
    refresh_plain = data.get("refresh_token")
    if not refresh_plain:
        return return_statement("", "Refresh token required", 400)

    try:
        now = datetime.now(timezone.utc)
        refresh_hash = hash_token(refresh_plain)

        # 1. Lookup & validate existing refresh token
        rows = fetch_records(
            table="refresh_tokens",
            where_clause="token = %s",
            params=(refresh_hash,),
            fetch_all=True
        )
        if not rows:
            return return_statement("", "Invalid refresh token", 401)

        row = rows[0]
        if row["revoked"] or row["expires_at"] < now:
            return return_statement("", "Refresh token expired or revoked", 401)

        user_id = row["user_id"]

        # 2. Revoke old refresh token
        update_records(
            "refresh_tokens",
            {"revoked": True},
            where_clause="id = %s",
            params=(row["id"],)
        )

        # 3. Generate & store new refresh token
        new_refresh_plain  = secrets.token_urlsafe(64)
        new_refresh_hash   = hash_token(new_refresh_plain)
        new_refresh_expiry = now + timedelta(days=30)

        insert_record(
            "refresh_tokens",
            {
              "user_id":    user_id,
              "token":      new_refresh_hash,
              "expires_at": new_refresh_expiry,
              "revoked":    False
            }
        )

        # 4. Generate & store new access token
        new_access_plain  = secrets.token_urlsafe(48)
        new_access_hash   = hash_token(new_access_plain)
        new_access_expiry = now + timedelta(days=7)

        insert_record(
            "session_tokens",
            {
              "userID":        user_id,
              "session_token": new_access_hash,
              "expires_at":    new_access_expiry,
              "revoked":       False,
              "ip_address":    request.remote_addr
            }
        )

        # 5. Return new tokens
        return return_statement(
            "",
            "Token refreshed",
            200,
            additional=[
              "access_token",  new_access_plain,
              "refresh_token", new_refresh_plain
            ]
        )

    except Exception:
        current_app.logger.exception("Error during token refresh")
        return return_statement("", "Internal server error", 500)

def reset_password_request():
    """
    Generates a reset token and emails a reset link.
    Requires only username.
    """
    data     = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()

    if not username:
        return return_statement("", "Username is required", 400)

    try:
        # find user by username (case-insensitive)
        users = fetch_records(
            "users",
            "LOWER(username) = LOWER(%s)",
            (username,),
            fetch_all=True
        )

        if not users:
            return return_statement("", "User not found", 404)

        user      = users[0]
        username  = user["username"]
        email     = user["email"]
        user_id   = user["userID"]
        reset_tok = 't0k3n' + secrets.token_urlsafe(16)
        hashed_tok = hashlib.sha256(reset_tok.encode()).hexdigest()
        expiry    = datetime.now(timezone.utc) + timedelta(hours=1)

        insert_record(
            "pass_reset_tokens",
            {
                "userID":      user_id,
                "reset_token": hashed_tok,
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
    Only requires username and token.
    """
    token    = request.args.get('token')
    username = request.args.get('username')

    if request.method == 'POST':
        password = request.form.get('password')
        confirm  = request.form.get('confirm_password')
        username = request.form.get('username') or username
        token    = request.form.get('token') or token

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
        token = hashlib.sha256(token.encode()).hexdigest()
        try:
            # verify reset token
            row = fetch_records(
                table="pass_reset_tokens",
                where_clause="reset_token = %s AND revoked = FALSE AND expires_at > %s",
                params=(token, datetime.now(timezone.utc)),
                order_by="created_at DESC",
                limit=1,
                fetch_all=False
            )

            if not row:
                return jsonify({"error": "Invalid or expired reset link"}), 400

            # fetch user and check username match
            users = fetch_records(
                table="users",
                where_clause="userID = %s AND LOWER(username) = LOWER(%s)",
                params=(row["userID"], username),
                fetch_all=True
            )
            if not users:
                return jsonify({"error": "Username does not match"}), 400

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

def profile():
    """
    POST /user/profile
    Body JSON: { "session_token": "<token>" }
    Returns: { "username": "...", "email": "..." }
    """
    data = request.get_json(silent=True) or {}
    token = data.get("session_token", "").strip()
    if not token:
        return return_statement("", "Session token is required", 400)

    username = authenticate_token(token)
    if not username:
        return return_statement("", "Invalid or expired session token", 401)

    try:
        # Fetch from the users table, not session_tokens
        user = fetch_records(
            table="users",
            where_clause="username = %s",
            params=(username,),
            fetch_all=False
        )
        if not user:
            return return_statement("", "User not found", 404)

        # Strip sensitive
        user.pop("password", None)

        # Return only the fields your front end needs
        profile_data = {
            "username": user["username"],
            "email":    user.get("email", "")
        }
        return return_statement(profile_data, "Profile fetched successfully", 200)

    except Exception:
        current_app.logger.exception("Error fetching profile")
        return return_statement("", "Internal server error", 500)

def submit_profile():
    """
    POST /user/submit-profile
    Body JSON: {
      "session_token": "...",
      "username":   "...",   # optional if not changing
      "email":      "...",   # optional if not changing
      "disable":    0|1,     # optional flags
      "delete":     0|1
    }
    """
    data = request.get_json(silent=True) or {}
    token       = (data.get("session_token") or "").strip()
    new_u       = (data.get("username")      or "").strip()
    new_e       = (data.get("email")         or "").strip()
    disable     = int(data.get("disable",  0))
    delete_acc  = int(data.get("delete",   0))

    if not token:
        return return_statement("", "Session token is required", 400)

    # 1) authenticate → gives current username
    current_username = authenticate_token(token)
    if not current_username:
        return return_statement("", "Invalid or expired session token", 401)

    try:
        # 2) fetch existing user record
        user = fetch_records(
            table="users",
            where_clause="username = %s",
            params=(current_username,),
            fetch_all=False
        )
        if not user:
            return return_statement("", "User not found", 404)
        user_id     = user["userID"]
        old_email   = user.get("email", "")
        # ——— handle delete/disable first ———
        if delete_acc:
            update_records("session_tokens",
                           {"revoked": True},
                           where_clause="userID = %s",
                           where_params=(user_id,))
            update_records("users",
                           {"deleted": True},
                           where_clause="userID = %s",
                           where_params=(user_id,))
            return return_statement(
                {"disable": disable, "delete": delete_acc},
                "Account deleted",
                200)

        if disable:
            update_records("session_tokens",
                           {"revoked": True},
                           where_clause="userID = %s",
                           where_params=(user_id,))
            update_records("users",
                           {"disabled": True},
                           where_clause="userID = %s",
                           where_params=(user_id,))
            return return_statement(
                {"disable": disable, "delete": delete_acc},
                "Account disabled",
                200)

        # ——— handle update ———
        # build update payload
        update_data = {}
        if new_u and new_u != current_username:
            update_data["username"] = new_u
        if new_e and new_e != old_email:
            update_data["email"] = new_e
            update_data["email_verified"] = False

        if update_data:
            # apply the update
            update_records(
                table="users",
                data=update_data,
                where_clause="userID = %s",
                where_params=(user_id,)
            )

            # if email changed, generate & send new verification token
            verification_sent = False
            if "email" in update_data:
                # revoke prior tokens
                update_records(
                    table="email_tokens",
                    data={"revoked": True},
                    where_clause="userID = %s",
                    where_params=(user_id,)
                )
                # new 6-digit code
                code = f"{random.randint(100000, 999999):06d}"
                expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
                insert_record(
                    "email_tokens",
                    {
                        "userID":      user_id,
                        "email_token": code,
                        "expires_at":  expiry,
                        "revoked":     False
                    }
                )
                # send mail
                send_verification_email(new_u or current_username, code, new_e)
                verification_sent = True

            # prepare response
            resp = {
                "username": update_data.get("username", new_u or current_username),
                "email":    update_data.get("email", old_email),
                "disable":  0,
                "delete":   0,
                "verificationSent": verification_sent
            }
            msg = "Profile updated" + ("; verification required" if verification_sent else "")
            return return_statement(resp, msg, 200)

        # nothing to do
        return return_statement("", "No changes requested", 400)

    except Exception:
        current_app.logger.exception("Error in submit-profile")
        return return_statement("", "Internal server error", 500)