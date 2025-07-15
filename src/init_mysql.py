import os
import logging
import subprocess
import threading
from mysql.connector import connect, Error
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Load configuration from environment variables
DB_HOST       = os.getenv("DB_HOST", "localhost")
DB_ROOT_USER  = os.getenv("DB_ROOT_USER", "root")
DB_ROOT_PASS  = os.getenv("DB_ROOT_PASSWORD")
DB_NAME       = os.getenv("DB_NAME", "chatcli")
DB_USER       = os.getenv("DB_USER", "chatcli_access")
DB_PASSWORD   = os.getenv("DB_PASSWORD")

def create_database_and_tables():
    """Create database and tables if they don't exist."""
    try:
        with connect(host=DB_HOST, user=DB_ROOT_USER, password=DB_ROOT_PASS, charset='utf8mb4',collation='utf8mb4_unicode_ci',use_unicode=True) as conn:
            conn.autocommit = False
            with conn.cursor() as cursor:
                logging.info("Connected to MySQL server as root.")
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                cursor.execute(f"USE `{DB_NAME}`;")

                table_statements = [
                    # email_subscribers (email not unique)
                    """
                    CREATE TABLE IF NOT EXISTS email_subscribers (
                      id             INT AUTO_INCREMENT PRIMARY KEY,
                      email          VARCHAR(255) NOT NULL UNIQUE,
                      subscribed_at  DATETIME DEFAULT CURRENT_TIMESTAMP
                    ) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """,

                    # users
                    """
                    CREATE TABLE IF NOT EXISTS users (
                      userID         INT AUTO_INCREMENT PRIMARY KEY,
                      username       VARCHAR(20)  NOT NULL UNIQUE,
                      password       VARCHAR(128) NOT NULL,
                      email          VARCHAR(100),
                      created_at     DATETIME     DEFAULT CURRENT_TIMESTAMP,
                      email_verified BOOLEAN      DEFAULT FALSE,
                      disabled       BOOLEAN      DEFAULT FALSE,
                      deleted        BOOLEAN      DEFAULT FALSE
                    ) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """,

                    # session_tokens
                    """
                    CREATE TABLE IF NOT EXISTS session_tokens (
                      tokenID        INT AUTO_INCREMENT PRIMARY KEY,
                      userID         INT NOT NULL,
                      session_token  CHAR(64) NOT NULL UNIQUE,  # SHA-256 hex
                      created_at     DATETIME     DEFAULT CURRENT_TIMESTAMP,
                      expires_at     DATETIME     NOT NULL,
                      revoked        BOOLEAN     DEFAULT FALSE,
                      ip_address     VARCHAR(45),
                      INDEX idx_sess_user (userID)
                    ) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """,

                    # refresh_tokens
                    """
                    CREATE TABLE IF NOT EXISTS refresh_tokens (
                      id            BIGINT UNSIGNED      AUTO_INCREMENT PRIMARY KEY,
                      user_id       INT                  NOT NULL,
                      token         CHAR(64)             NOT NULL UNIQUE,  # SHA-256 hex
                      created_at    DATETIME             NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      expires_at    DATETIME             NOT NULL,
                      revoked       BOOLEAN              NOT NULL DEFAULT FALSE,
                      INDEX idx_ref_user    (user_id),
                      INDEX idx_ref_expires (expires_at),
                      FOREIGN KEY (user_id) REFERENCES users(userID)
                    ) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """,

                    # email_tokens
                    """
                    CREATE TABLE IF NOT EXISTS email_tokens (
                      tokenID      INT AUTO_INCREMENT PRIMARY KEY,
                      userID       INT NOT NULL,
                      email_token  CHAR(6)        NOT NULL,  # 6-digit code
                      created_at   DATETIME       DEFAULT CURRENT_TIMESTAMP,
                      expires_at   DATETIME       NOT NULL,
                      revoked      BOOLEAN        DEFAULT FALSE,
                      INDEX idx_email_user (userID)
                    ) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """,

                    # pass_reset_tokens
                    """
                    CREATE TABLE IF NOT EXISTS pass_reset_tokens (
                      tokenID      INT AUTO_INCREMENT PRIMARY KEY,
                      userID       INT NOT NULL,
                      reset_token  CHAR(64)   NOT NULL UNIQUE,  # SHA-256 hex
                      created_at   DATETIME       DEFAULT CURRENT_TIMESTAMP,
                      expires_at   DATETIME       NOT NULL,
                      revoked      BOOLEAN        DEFAULT FALSE,
                      INDEX idx_reset_user (userID)
                    ) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """,

                    # chats
                    """
                    CREATE TABLE IF NOT EXISTS chats (
                      chatID     INT AUTO_INCREMENT PRIMARY KEY,
                      created_at DATETIME          DEFAULT CURRENT_TIMESTAMP,
                      type       ENUM('private','group') NOT NULL DEFAULT 'private'
                    ) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """,

                    # participants
                    """
                    CREATE TABLE IF NOT EXISTS participants (
                      chatID INT NOT NULL,
                      userID INT NOT NULL,
                      PRIMARY KEY (chatID, userID),
                      INDEX idx_part_user (userID, chatID),
                      CONSTRAINT fk_participants_chats
                        FOREIGN KEY (chatID) REFERENCES chats(chatID),
                      CONSTRAINT fk_participants_users
                        FOREIGN KEY (userID) REFERENCES users(userID)
                    ) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """,

                    # messages
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                      messageID INT AUTO_INCREMENT PRIMARY KEY,
                      chatID    INT NOT NULL,
                      userID    INT NOT NULL,
                      message   TEXT,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                      INDEX idx_msg_chat_ts (chatID, timestamp)
                    ) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """
                ]

                # execute each CREATE
                for stmt in table_statements:
                    cursor.execute(stmt)
                logging.info("All tables created or verified successfully.")

                # application user privileges
                cursor.execute(
                    "CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s;",
                    (DB_USER, DB_HOST, DB_PASSWORD)
                )
                cursor.execute(
                    f"GRANT SELECT, INSERT, UPDATE, DELETE ON `{DB_NAME}`.* TO %s@%s;",
                    (DB_USER, DB_HOST)
                )
                logging.info(f"User '{DB_USER}' granted privileges on `{DB_NAME}`.")

                conn.commit()
                logging.info("Database setup committed.")

    except Error as e:
        logging.error(f"MySQL Error during setup: {e}")
        raise

def run_application(flask_script="main.py", fastapi_script="app/websockets/main.py"):
    """Launch the Flask and FastAPI scripts in separate CMD windows with clear titles."""
    try:
        logging.info(f"Starting Flask app in new CMD: {flask_script}")
        subprocess.Popen([
            "cmd.exe", "/c",
            "start", "Flask Backend",      # <-- window title
            "cmd.exe", "/k", f"python {flask_script}"
        ])

        logging.info(f"Starting FastAPI app in new CMD: {fastapi_script}")
        subprocess.Popen([
            "cmd.exe", "/c",
            "start", "FastAPI Backend",    # <-- window title
            "cmd.exe", "/k", f"python {fastapi_script}"
        ])

    except Exception as e:
        logging.error(f"Error starting applications: {e}")
        raise

if __name__ == "__main__":
    create_database_and_tables()
    run_application()