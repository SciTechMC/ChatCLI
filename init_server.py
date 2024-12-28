import subprocess
import mysql.connector
import os

try:
    # Establishing the connection
    with mysql.connector.connect(host="localhost", user="root", password="1234") as conn:
        cursor = conn.cursor()

        # Create the database if it doesn't already exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS chatcli;")
        cursor.execute("USE chatcli;")

        # Create the Users table if not exists
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

        # Create the Chats table if not exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Chats (
            chatID INT AUTO_INCREMENT PRIMARY KEY,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            type ENUM('group', 'private') DEFAULT 'private',
            last_message DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Create the Participants table if not exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Participants (
            chatID INT,
            userID INT,
            FOREIGN KEY (chatID) REFERENCES Chats(chatID) ON DELETE CASCADE,
            FOREIGN KEY (userID) REFERENCES Users(userID) ON DELETE CASCADE,
            PRIMARY KEY (chatID, userID)
        );
        """)

        # Create the Messages table if not exists
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

        # Insert or update the test user
        cursor.execute("""
        INSERT INTO Users (username, password, email)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE password = VALUES(password), email = VALUES(email);
        """, ('1', '1', 'jan.vdcg@gmail.com'))

        # Create MySQL user and grant privileges
        cursor.execute("""
        CREATE USER IF NOT EXISTS 'chatcli_access'@'localhost' IDENTIFIED WITH caching_sha2_password BY 'test1234';
        """)

        cursor.execute("""
        GRANT ALL PRIVILEGES ON chatcli.* TO 'chatcli_access'@'localhost';
        """)

        conn.commit()

        print("Database setup complete.")
except mysql.connector.Error as err:
    print(f"Error: {err}")

# Run server scripts in new console windows with error handling
try:
    subprocess.Popen("python server_ws.py", creationflags=subprocess.CREATE_NEW_CONSOLE)
    subprocess.Popen("python server_flask.py", creationflags=subprocess.CREATE_NEW_CONSOLE)
except Exception as e:
    print(f"Error starting servers: {e}")
