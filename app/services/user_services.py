from app.services.base_services import return_statement, get_db
from app.services.mail_services import send_email
from flask import request, jsonify, render_template
import mysql.connector
import random
import string
import bcrypt
import re

def register():
    """
    Registers a new user in the system.
    """
    client = request.get_json()
    username = client.get("username").lower()
    password = client.get("password")
    email = client.get("email")
    print("username " + username)
    user_id = 0

    # Validate input fields
    if not username or not password:
        return return_statement("", "Username and password are required", 400)
    if any(char in r'"%\'()*+,/:;<=>?@[\]^{|}~` ' for char in username):
        return return_statement("", "Username includes bad characters", 400)
    if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA0-9-.]+$', email):
        return return_statement("", "Invalid email address", 400)
    if (
            len(password) < 8 or
            not any(char.isupper() for char in password) or
            not any(char.islower() for char in password) or
            not any(char.isdigit() for char in password) or
            not any(char in string.punctuation for char in password)
    ):
        return return_statement("",
                                "Your password must contain at least 8 characters, including an uppercase letter, a lowercase letter, a number, and a special character!",
                                400)

    password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    conn = get_db()
    cursor = conn.cursor()
    try:
        # Check if the user already exists
        cursor.execute("SELECT * FROM Users WHERE username = %s;", (username,))
        user_fetched = cursor.fetchone()
        if user_fetched and user_fetched[5] != 0:
            return return_statement("", f"User '{username}' already exists", 400)

        if not user_fetched:
            cursor.execute(
                "INSERT INTO Users (username, password, email, email_verified) VALUES (%s, %s, %s, FALSE)",
                (username, password, email,)
            )
        else:
            cursor.execute("""
            UPDATE users
            SET username = %s, password = %s, email = %s, created_at = NOW()
            WHERE userID = %s;
                """,
                (username, password, email, user_fetched[0],)
            )
            cursor.execute("""
            UPDATE email_tokens
            SET is_disabled = TRUE
            WHERE NOW() <= DATE_ADD(created_at, INTERVAL 6 MINUTE) AND userID = %s;
            """, (user_fetched[0],))

        conn.commit()

        cursor.execute(
            "SELECT * FROM Users WHERE username = %s", (username,)
        )
        last_entry = cursor.fetchone()
        user_id = last_entry[0]

        email_token = random.randint(100000,999999)

        # Insert the new user
        cursor.execute(
            "INSERT INTO email_tokens (userID, email_token) VALUES (%s, %s)",
            (user_id, email_token)
        )
        conn.commit()

        # Compose the email
        subject = "ChatCLI Account Verification Code"
        body = f"""
Dear {username},

Thank you for registering with ChatCLI. To complete your registration, please use the verification code provided below.

Verification Code: {email_token}

This code is valid for the next 5 minutes. Please enter it in the application. If you did not request this code, please disregard this email.

If you encounter any issues or need assistance, feel free to contact our support team on github (https://github.com/SciTechMC/ChatCLI/issues/new/choose) or by email using chatcli.official+support@gmail.com.

Best regards,
The ChatCLI Team
https://github.com/SciTechMC/ChatCLI
            """
    except Exception as e:
        return return_statement("", str(e), 500)

    try:
        response = send_email(body, subject, email)

        # Check if the email was successfully sent
        if isinstance(response, list) and not response[0]:
            return return_statement("", response[1], 500)

        # https://chatgpt.com/share/679a219d-1a24-800f-ba48-b93c4c403ac7

        # If email sent successfully
        return return_statement("Email sent successfully!")

    except Exception as e:
        # If an exception occurs, roll back the transaction and return error
        conn.rollback()
        return return_statement("", str(e), 500)

    finally:
        # Ensure the cursor is always closed to release resources
        cursor.close()

def verify_email():
    client = request.get_json()
    username = client.get("username").lower()
    client_token = client.get("email_token")
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT email_token FROM email_tokens 
        WHERE userID = (SELECT userID from users WHERE username = %s) 
        AND NOW() <= DATE_ADD(created_at, INTERVAL 5 MINUTE)
        AND is_disabled = FALSE
        ORDER BY created_at DESC
        LIMIT 1;
        """, (username,))
        server_token = cursor.fetchone()
        if server_token is None or str(server_token[0]) != str(client_token):
            return return_statement("", "Invalid code!", 400)
        else:
            cursor.execute("""
            UPDATE users
            SET email_verified = TRUE
            WHERE username = %s;
            """, (username,))
            return return_statement("Email verified!")

    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor.close()

def login():
    """
    Logs in a user by validating credentials and generating a session token.
    """
    client = request.get_json()
    username = client.get("username").lower()
    password = client.get("password")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch user data based on username
        cursor.execute("SELECT userID, password FROM Users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if not user:
            return return_statement("", "Username not found!", 404)
        if not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
            return return_statement("", "Invalid password", 400)

        # Generate a new session token
        session_token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=64))
        session_token_encrypted = bcrypt.hashpw(session_token.encode("utf-8"), bcrypt.gensalt())
        # Insert the session token into the session_tokens table
        cursor.execute("""
            INSERT INTO session_tokens (userID, session_token, ip_address, is_active) 
            VALUES (%s, %s, %s, TRUE)
        """, (user["userID"], session_token_encrypted, request.remote_addr))
        conn.commit()

        return return_statement("Login Successful!", additional=["session_token", session_token])
    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor.close()

def reset_password_request():
    client = request.get_json()
    username = client.get("data")
    have_username = False
    email = ""
    userID = 0

    if not username:
        return return_statement("", "Invalid input", 400)

    token = 't0k3n' + ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    cursor = get_db().cursor(dictionary=True)

    if re.match(r'^[a-zA-Z0-9.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', username):
        cursor.execute("SELECT username, userID FROM users WHERE email = %s", (username,))
        query = cursor.fetchall()

        if len(query) > 1:
            have_username = False
        elif len(query) == 1:
            username = query[0]["username"]
            userID = query[0]["userID"]
            have_username = True
        else:
            return return_statement("", "User not found", 404)
    else:
        cursor.execute("SELECT email, userID FROM users WHERE username = %s", (username,))
        query = cursor.fetchone()

        if query:
            email = query["email"]
            userID = query["userID"]
            have_username = True
        else:
            return return_statement("", "User not found", 404)

    db = get_db()
    cursor = db.cursor()

    cursor.execute("INSERT INTO pass_reset (reset_token, userID) VALUES (%s, %s)", (token, userID,))
    db.commit()
    subject = "Password Reset Request for Your Account"

    if have_username:
        reset_link = f"https://chat.puam.be/reset-password?token={token}&username={username}"
    else:
        reset_link = f"https://chat.puam.be/verify-username?token={token}"

    body = f"""
Dear {username},

We received a request to reset the password for your account. If you made this request, click the link below to reset your password:

Reset Password: {reset_link}

If you did not request this, ignore this email.

Best regards,  
The ChatCLI Team  
https://github.com/SciTechMC/ChatCLI
    """

    try:
        response = send_email(body, subject, email)

        if isinstance(response, list) and not response[0]:
            return return_statement("", response[1], 500)

        return return_statement("Email sent successfully!")

    except Exception as e:
        db.rollback()
        return return_statement("", str(e), 500)
    finally:
        print("email sent to", email)
        cursor.close()

def reset_password():
    token = request.args.get('token')
    username = request.args.get('username')

    # If it's a POST request, try getting the username from the form data
    if request.method == 'POST' and not username:
        username = request.form.get('username')

    # Check if username is still None
    if not username:
        return jsonify({"error": "Missing username in request"}), 400

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        cursor.execute("SELECT userID FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": f"User does not exist: {username}"}), 404

        user_id = user[0]

        # Get passwords
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validate passwords
        if password != confirm_password:
            return jsonify({"error": "Passwords do not match"}), 400

        if (
            len(password) < 8 or
            not any(char.isupper() for char in password) or
            not any(char.islower() for char in password) or
            not any(char.isdigit() for char in password) or
            not any(char in string.punctuation for char in password)
        ):
            return jsonify({"error": "Password must contain at least 8 characters, an uppercase letter, a lowercase letter, a number, and a special character!"}), 400

        # Hash and update password
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        cursor.execute("UPDATE users SET password = %s WHERE userID = %s", (hashed_password, user_id))
        conn.commit()

        return jsonify({"message": "Password reset successfully"}), 200

    return render_template("reset_password.html", username=username, token=token)