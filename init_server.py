import subprocess
import mysql.connector

try:
    # Connect to MySQL server
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234"
    )
    cursor = conn.cursor()

    # Create the database if it doesn't already exist
    cursor.execute("CREATE DATABASE IF NOT EXISTS chatcli;")

    # Switch to the newly created database
    cursor.execute("USE chatcli;")

    # Create the Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        userID INT AUTO_INCREMENT PRIMARY KEY,         -- Auto-incrementing IDs
        username VARCHAR(20) NOT NULL UNIQUE,          -- Unique username with max length of 20
        password VARCHAR(64) NOT NULL,                 -- Password field with max length of 64
        email VARCHAR(100),                            -- Email field with max length of 100
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- Default current timestamp
        key VARCHAR(24)                                -- Key used to identify the user
    );
    """)

    # Create the Chats table
    cursor.execute("""
    CREATE TABLE Chats (
        chatID INT AUTO_INCREMENT PRIMARY KEY,  -- Chat identifier
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- Date and time when the chat was created
        type ENUM('group', 'private') DEFAULT 'private',  -- Type of chat (group or private)
        last_message DATETIME DEFAULT CURRENT_TIMESTAMP  -- Timestamp for the last message in the chat
    );
    """)

    # Create the Participants table
    cursor.execute("""
    CREATE TABLE Participants (
        chatID INT,  -- Chat ID
        userID INT,  -- User ID
        FOREIGN KEY (chatID) REFERENCES Chats(chatID) ON DELETE CASCADE,  -- Link to Chats table
        FOREIGN KEY (userID) REFERENCES Users(userID) ON DELETE CASCADE,  -- Link to Users table
        PRIMARY KEY (chatID, userID)  -- Ensure unique combination of chat and user
    );
    """)

    # Create the Messages table
    cursor.execute("""
    CREATE TABLE Messages (
        messageID INT AUTO_INCREMENT PRIMARY KEY,  -- Message identifier
        chatID INT,  -- Reference to Chats table
        userID INT,  -- Reference to the user who sent the message
        message TEXT,  -- The content of the message
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,  -- Timestamp for when the message was sent
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

    # Create a user for MySQL access
    cursor.execute("""
    CREATE USER 'chatcli_access'@'localhost' IDENTIFIED WITH caching_sha2_password BY 'test1234';
    """)

    # Grant privileges to the chatcli_access user
    cursor.execute("""
    GRANT ALL PRIVILEGES ON chatcli.* TO 'chatcli_access'@'localhost';
    """)

    # Commit changes and close the connection
    conn.commit()

    print("Database setup complete.")

except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    if conn.is_connected():
        conn.close()

# Run servers in new console windows
subprocess.Popen("python server_ws.py", creationflags=subprocess.CREATE_NEW_CONSOLE)
subprocess.Popen("python server_flask.py", creationflags=subprocess.CREATE_NEW_CONSOLE)
