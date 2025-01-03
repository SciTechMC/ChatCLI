import subprocess
import mysql.connector
import os

try:
    # Establishing the connection
    with mysql.connector.connect(host="localhost", user="root", password="1234") as conn:
        cursor = conn.cursor()

        # Create the database if it doesn't already exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS chatcli_prod;")
        cursor.execute("USE chatcli_prod;")

        # Create tables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            userID INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(20) NOT NULL UNIQUE,
            password VARCHAR(64) NOT NULL,
            email VARCHAR(100),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_key VARCHAR(24)
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Chats (
            chatID INT AUTO_INCREMENT PRIMARY KEY,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            type ENUM('group', 'private') DEFAULT 'private',
            last_message DATETIME DEFAULT CURRENT_TIMESTAMP,
            testing_chat_caract VARCHAR(20) UNIQUE
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
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chatID) REFERENCES Chats(chatID) ON DELETE CASCADE,
            FOREIGN KEY (userID) REFERENCES Users(userID) ON DELETE CASCADE
        );
        """)
        
        # Create MySQL user and grant privileges
        cursor.execute("""
        CREATE USER IF NOT EXISTS 'production_chatcli'@'localhost' IDENTIFIED WITH caching_sha2_password BY 'S3cret#Code1234';
        """)
        cursor.execute("""
        GRANT SELECT, INSERT, UPDATE, DELETE ON chatcli_prod.* TO 'production_chatcli'@'localhost';
        """)

        conn.commit()
        print("Database setup complete.")
except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    if conn.is_connected():
        conn.close()

# Run server scripts
try:
    subprocess.Popen(["python", "server_ws.py"], creationflags=subprocess.CREATE_NEW_CONSOLE)
    subprocess.Popen(["python", "server_flask.py"], creationflags=subprocess.CREATE_NEW_CONSOLE)
except Exception as e:
    print(f"Error starting servers: {e}")
