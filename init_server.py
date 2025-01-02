import subprocess
import mysql.connector
import os

try:
    # Establishing the connection
    with mysql.connector.connect(host="localhost", user="root", password="1234") as conn:
        cursor = conn.cursor()

        match input("Reset database (y/n)? "):
            case "y":
                try:
                    cursor.execute("DROP DATABASE IF EXISTS chatcli;")  # Corrected syntax
                    conn.commit()
                    print("Database 'chatcli' has been reset.")
                except mysql.connector.Error as e:
                    print(f"Error while resetting database: {e}")

        # Create the database if it doesn't already exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS chatcli;")
        cursor.execute("USE chatcli;")

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

        # Insert users explicitly
        cursor.execute("""
        INSERT IGNORE INTO Users (username, password, email, user_key)
        VALUES (%s, %s, %s, %s);
        """, ('test', '1', 'jan.vdcg@gmail.com', '1'))
        print("Inserted first user")

        cursor.execute("""
        INSERT IGNORE INTO Users (username, password, email, user_key)
        VALUES (%s, %s, %s, %s);
        """, ('tester', '2', 'jan.vdcg@gmail.com', '2'))
        print("Inserted second user")

        # Insert into Chats
        cursor.execute("INSERT IGNORE INTO Chats (type,testing_chat_caract) VALUES ('private','yes');")

        # Insert participants
        cursor.execute("INSERT IGNORE INTO Participants (chatID, userID) VALUES (%s, %s);", (1, 1))
        cursor.execute("INSERT IGNORE INTO Participants (chatID, userID) VALUES (%s, %s);", (1, 2))

        # Create MySQL user and grant privileges
        cursor.execute("""
        CREATE USER IF NOT EXISTS 'chatcli_access'@'localhost' IDENTIFIED WITH caching_sha2_password BY 'test1234';
        """)
        cursor.execute("""
        GRANT SELECT, INSERT, UPDATE, DELETE ON chatcli.* TO 'chatcli_access'@'localhost';
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
