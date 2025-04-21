import mysql.connector
from mysql.connector import Error
import subprocess

def setup_database():
    try:
        # Connect to MySQL as root
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Bunny-S3crEt"
        )

        if connection.is_connected():
            print("Connected to MySQL server as root.")

            cursor = connection.cursor()

            # Create the database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS chatcli_access;")
            print("Database 'chatcli_access' created or already exists.")

            # Use the database
            cursor.execute("USE chatcli_access;")

            # Create tables
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_subscribers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                subscribed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                userID INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(20) NOT NULL UNIQUE,
                password VARCHAR(128) NOT NULL,
                email VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                email_verified BOOLEAN DEFAULT FALSE
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_tokens (
                tokenID INT AUTO_INCREMENT PRIMARY KEY,
                userID INT,
                session_token VARCHAR(128),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (userID) REFERENCES Users(userID)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_tokens (
                tokenID INT AUTO_INCREMENT PRIMARY KEY,
                userID INT,
                email_token INT NOT NULL CHECK (email_token BETWEEN 100000 AND 999999),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_disabled BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (userID) REFERENCES Users(userID)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS pass_reset (
                tokenID INT AUTO_INCREMENT PRIMARY KEY,
                reset_token VARCHAR(128),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                userID INT,
                FOREIGN KEY (userID) REFERENCES Users(userID)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Chats (
                chatID INT AUTO_INCREMENT PRIMARY KEY,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                type ENUM('group', 'private') DEFAULT 'private',
                last_message DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Participants (
                chatID INT,
                userID INT,
                FOREIGN KEY (chatID) REFERENCES Chats(chatID) ON DELETE CASCADE,
                FOREIGN KEY (userID) REFERENCES Users(userID) ON DELETE CASCADE,
                PRIMARY KEY (chatID, userID)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Messages (
                messageID INT AUTO_INCREMENT PRIMARY KEY,
                chatID INT,
                userID INT,
                message TEXT(2000),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chatID) REFERENCES Chats(chatID) ON DELETE CASCADE,
                FOREIGN KEY (userID) REFERENCES Users(userID) ON DELETE CASCADE
            );
            """)

            print("Tables created successfully.")

            # Create a MySQL user and grant privileges
            cursor.execute("""
            CREATE USER IF NOT EXISTS 'chatcli_user'@'localhost' IDENTIFIED BY 'S3cret#Code1234';
            """)
            cursor.execute("""
            GRANT SELECT, INSERT, UPDATE, DELETE ON chatcli_access.* TO 'chatcli_user'@'localhost';
            """)
            print("User 'chatcli_user' created and granted privileges.")

            # Commit changes
            connection.commit()

    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection closed.")

if __name__ == "__main__":
    setup_database()
    try:
        subprocess.run(["python", "main.py"], check=True)
    except Exception as e:
        print(f"Error: {e}")