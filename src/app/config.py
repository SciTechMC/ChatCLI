import os

def email_acc():
    return os.getenv("EMAIL_USER")

def email_pssw():
    return os.getenv("EMAIL_PASSWORD")

def db_login():
    return {
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "db": os.getenv("DB_NAME", "chatcli"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 3306))
    }
    
VALID_TABLES = {
    "users",
    "email_subscribers",
    "session_tokens",
    "email_tokens",
    "pass_reset_tokens",
    "chats",
    "participants",
    "messages",
    "refresh_tokens"
}