import json
import random
import string
from flask import Flask, request, jsonify, g, render_template_string
import re
import mysql.connector
import bcrypt
import db_envs
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


#waitress-serve --host=0.0.0.0 --port=5000 --threads=4 --workers=9 --ssl-certfile=/certifs/cert.pem --ssl-keyfile=/certifs/privkey.pem server_flask:app

app = Flask(__name__)

with open("mail_info.json", "r") as f:
    data = json.load(f)
    email_pssw = data["pssw"]
    email_acc = data["acc"]

# ---------------------------- DATABASE UTILITIES ----------------------------

def get_db():
    """
    :return: A MySQL database connection stored in Flask's 'g' object.
    """
    if 'db' not in g:
        env = db_envs.dev()  # Fetch database credentials
        g.db = mysql.connector.connect(
            host="localhost",
            user=env["user"],
            password=env["password"],
            database=env["db"]
        )
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """
    Ensures the database connection is closed after each request.
    :param exception: Any exception raised during the request.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

# ---------------------------- UTILITY FUNCTIONS ----------------------------

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
    """
    Standardized JSON response.
    """
    return jsonify({
        "response": response,
        "error": error,
        **(dict([additional]) if additional else {})
    }), status_code

def send_email(message,subject,receiver):

    msg = MIMEMultipart()
    msg['From'] = email_acc
    msg['To'] = receiver
    msg['Subject'] = subject

    # Attach the body to the email
    msg.attach(MIMEText(message, 'plain'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_acc, email_pssw)
            text = msg.as_string()
            server.sendmail(email_acc, receiver, text)
            return True
    except Exception as e:
        return [False, str(e)]

# ---------------------------- ROUTES ----------------------------

@app.route("/verify-connection", methods=["POST", "GET"])
def verify_connection():
    """
    Test route to verify server is reachable.
    """
    # Handle POST request
    if request.method == "POST":
        # Ensure the JSON body exists
        client_data = request.get_json()
        if not client_data:
            return return_statement("", "Invalid request!", 400)

        version = client_data.get("version")
        if version == "post-alpha-dev-build":
            return return_statement(response="Hello World!")
        else:
            return return_statement("", "Incompatible client version!", 400)

    # Handle GET request
    elif request.method == "GET":
        return return_statement("", "Incompatible client version!", 400)

    # Fallback (should not be reached)
    return return_statement("", "Unsupported HTTP method!", 405)

#ACCOUNT BS

@app.route("/register", methods=["POST"])
def register():
    """
    Registers a new user in the system.
    """
    client = request.get_json()
    username = client.get("username").lower()
    password = client.get("password")
    email = client.get("email")
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
        cursor.execute("SELECT 1 FROM Users WHERE username = %s;", (username,))
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
            UPDATE users
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

        # Set up the email message
        msg = MIMEMultipart()
        msg['From'] = email_acc
        msg['To'] = email
        msg['Subject'] = subject

        # Attach the body to the email
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(email_acc, email_pssw)
                text = msg.as_string()
                server.sendmail(email_acc, email, text)
                return return_statement("Email sent Successfully")
        except Exception as e:
            conn.rollback()
            return return_statement("",f"Error sending email: {e}", 500)

    except Exception as e:
        conn.rollback()
        return return_statement("", str(e), 500)
    finally:
        cursor.close()

@app.route("/resend-email", methods=["POST"])
def resend_email():
    client = request.get_json()
    username = client.get("username").lower()
    client_token = client.get("email_token")
    conn = get_db()
    cursor = conn.cursor()
    try:
        email_token = random.randint(100000, 999999)
        cursor.execute("""
        UPDATE email_tokens
        SET email_token = %s
        WHERE userID = (SELECT userID FROM users WHERE username = %s);
        """, (email_token,username,))
    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor.close()

@app.route("/verify-email", methods=["POST"])
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
        ORDER BY created_at DESC;
        """, (username,))
        server_token = cursor.fetchone()
        if server_token[0] == client_token:
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

@app.route("/login", methods=["POST"])
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

@app.route("/reset-password-request", methods=["POST"])
def reset_password_request():
    client = request.json().get("data")
    username = ""
    have_username = False
    email = ""
    userID = 0
    if not client:
        return return_statement("", "Invalid input", 400)
    token = 't0k3n' + ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    if re.match(r'^[a-zA-Z0-9.+-]+@[a-zA-Z0-9-]+.[a-zA-Z0-9-.]+$', client):
        cursor = get_db().cursor(dictionary=True)
        cursor.execute("""
        SELECT username, userID FROM users
        WHERE email = %s
        """, (client,))
        query = cursor.fetchall()

        if len(query) > 1:
            have_username = False
        elif len(query) == 1:
            username = query[0].get("username")
            userID = query[0].get("userID")
            have_username = True
        else:
            return return_statement("", "User not found", 404)

    else:
        username = client.get("data")
        cursor = get_db().cursor(dictionary=True)
        cursor.execute("""
        SELECT email, userID FROM users
        WHERE username = %s
        """, (client,))
        query = cursor.fetchone()
        email = query.get("email")
        have_username = True
        userID = query.get("userID")
        if not email:
            return return_statement("", "User not found", 404)

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
    INSERT INTO pass_reset (reset_token, userID)
    (%,%s)
    """, (token, userID,))

    subject = "Password Reset Request for Your Account"
    body = f"""
Dear {username},

We received a request to reset the password for your account associated with this email address. If you made this request, please click the link below to reset your password:

Reset Password : https://fortbow.duckdns.org:5000/reset-password?token={token}&?username={have_username}

This link will expire in [timeframe, e.g., 24 hours] for security reasons.

If you did not request a password reset, please ignore this email or contact our support team if you have concerns about your account's security.

Best regards,
The ChatCLI Team
https://github.com/SciTechMC/ChatCLI"""

    sent_mail = send_email(body,subject,email)

    if not sent_mail[0]:
        db.rollback()
        return return_statement("",sent_mail[1],500)

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    # Get token and username from query parameters
    token = request.args.get('token')
    username = request.args.get('username')
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        if username == "False":  # Username verification form submitted
            # Get the username from the form
            username_input = request.form.get('username')

            cursor.execute("SELECT * FROM users where username = %s", (username,))
            # TODO: Verify if the username exists in the database
            # Example response for demonstration purposes
            user_exists = True  # Replace with actual database check
            if user_exists:
                return jsonify({"message": "Username verified. Proceed to password reset.", "username": username_input})
            else:
                return jsonify({"error": "Username does not exist"}), 404
        else:  # Password reset form submitted
            # Get the passwords from the form
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            # Check if the passwords match
            if password != confirm_password:
                return jsonify({"error": "Passwords do not match"}), 400

            # TODO: Reset the user's password in the database
            # Example response for demonstration purposes
            return jsonify({"message": "Password reset successfully"})

    # Handle GET request
    if username == "False":
        # Render the username verification page
        return render_template_string("username_input.html")
    else:
        # Render the password reset form
        return render_template_string("reset_password.html")

    subject = "Password Reset Request for Your Account"
    body = f"""
    Dear {username},

    We received a request to reset the password for your account associated with this email address. If you made this request, please click the link below to reset your password:

    Reset Password : https://fortbow.duckdns.org:5000/reset-password?token={token}&?username={have_username}

    This link will expire in [timeframe, e.g., 24 hours] for security reasons.

    If you did not request a password reset, please ignore this email or contact our support team if you have concerns about your account's security.

    Best regards,
    The ChatCLI Team
    https://github.com/SciTechMC/ChatCLI"""

    sent_mail = send_email(body, subject, email)

    if not sent_mail[0]:
        db.rollback()
        return return_statement("", sent_mail[1], 500)

#CHATTING BS

@app.route("/fetch-chats", methods=["POST"])
def fetch_chats():
    """
    Fetches chat participants for a user.
    """
    client = request.get_json()
    username = client.get("username").lower()
    session_token = client.get("session_token")

    # Verify the session token instead of user_key
    if not verif_user(username, session_token):
        return return_statement("", "Unable to verify user!", 400)

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT DISTINCT u.username
        FROM Users u
        JOIN Participants p ON u.userID = p.userID
        WHERE p.chatID IN (
            SELECT chatID FROM Participants
            WHERE userID = (SELECT userID FROM Users WHERE username = %s)
        ) AND u.userID != (SELECT userID FROM Users WHERE username = %s)
        """, (username, username))

        chats = [row[0] for row in cursor.fetchall()]
        return return_statement(chats)
    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor.close()

@app.route("/create-chat", methods=["POST"])
def create_chat():
    """
    Creates a new chat between two users.
    """
    client = request.get_json()
    username = client.get("username").lower()
    receiver = client.get("receiver").lower()
    session_token = client.get("session_token")

    if not username or not receiver:
        return return_statement("", "Some statements are empty", 404)

    # Verify the session token instead of user_key
    if not verif_user(username, session_token):
        return return_statement("", "Unable to verify user!", 400)

    conn = get_db()
    cursor = conn.cursor()
    try:
        # Get user IDs for participants
        cursor.execute("SELECT userID FROM Users WHERE LOWER(username) = %s;", (username,))
        sender_id = cursor.fetchone()

        cursor.execute("SELECT userID FROM Users WHERE LOWER(username) = %s;", (receiver,))
        receiver_id = cursor.fetchone()

        if not sender_id or not receiver_id:
            return return_statement("", "Sender or receiver not found!", 400)

        sender_id, receiver_id = sender_id[0], receiver_id[0]

        # Create a new chat
        cursor.execute("INSERT INTO Chats () VALUES ();")
        cursor.execute("SELECT LAST_INSERT_ID();")
        chat_id = cursor.fetchone()[0]

        # Add participants
        cursor.execute("INSERT INTO Participants (chatID, userID) VALUES (%s, %s);", (chat_id, sender_id))
        cursor.execute("INSERT INTO Participants (chatID, userID) VALUES (%s, %s);", (chat_id, receiver_id))

        conn.commit()
        return return_statement(f"Chat created successfully!", "", 200)
    except mysql.connector.Error as e:
        conn.rollback()
        return return_statement("", str(e), 500)
    finally:
        cursor.close()

@app.route("/receive-message", methods=["POST"])
def receive_message():
    """
    Stores a message sent from one user to another.
    """
    client = request.get_json()
    username = client.get("username").lower()
    receiver = client.get("receiver").lower()
    session_token = client.get("session_token")  # Changed to session_token
    message = client.get("message")

    # Verify user with session token instead of user_key
    if not verif_user(username, session_token):
        return return_statement("", "Unable to verify user!", 400)

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT chatID FROM Participants
        WHERE userID IN (SELECT userID FROM Users WHERE username = %s)
        AND chatID IN (
            SELECT chatID FROM Participants
            WHERE userID = (SELECT userID FROM Users WHERE username = %s)
        )
        """, (username, receiver,))
        chat_id = cursor.fetchone()

        if not chat_id:
            return return_statement("", "No chat found between users!", 400)

        chat_id = chat_id[0]

        # Insert message
        cursor.execute("""
        INSERT INTO Messages (chatID, userID, message)
        VALUES (%s, (SELECT userID FROM Users WHERE username = %s), %s)
        """, (chat_id, username, message,))
        conn.commit()
        return return_statement("Message sent successfully!")
    except mysql.connector.Error as e:
        return return_statement("", str(e), 500)
    finally:
        cursor.close()

# ---------------------------- RUN SERVER ----------------------------

if __name__ == "__main__":
    cert_path = '/etc/letsencrypt/live/<your-domain>/cert.pem'
    key_path = '/etc/letsencrypt/live/<your-domain>/privkey.pem'

    app.run(host="0.0.0.0",debug=True, ssl_context=('./certifs/fullchain.pem', './certifs/privkey.pem'))
