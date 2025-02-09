import subprocess

imports = ["asyncio", "aiomysql", "websockets","requests", "json", "rich", "mysql.connector", "cryptography", "smtp", "bcrypt"]
for install in imports:
    subprocess.Popen(f"pip install {install}", creationflags=subprocess.CREATE_NEW_CONSOLE)

import asyncio
import aiomysql
import db_envs  # Importing the module to get database credentials


async def setup_database():
    db_config = (db_envs.prod())
    conn = await aiomysql.connect(
        host="localhost",
        user='root',
        password='1234'
    )
    try:
        async with conn.cursor() as cursor:
            # Create the database if it doesn't already exist
            await cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_config['db']};")
            await cursor.execute(f"USE {db_config['db']};")

            # Create tables
            await cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_subscribers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                subscribed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)

            await cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                userID INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(20) NOT NULL UNIQUE,
                password VARCHAR(128) NOT NULL,
                email VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                email_verified BOOLEAN DEFAULT FALSE
            );
            """)

            await cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_tokens (
                tokenID INT AUTO_INCREMENT PRIMARY KEY,
                userID INT,
                session_token VARCHAR(128),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (userID) REFERENCES users(userID)
            );
            """)

            await cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_tokens (
                tokenID INT AUTO_INCREMENT PRIMARY KEY,
                userID INT,
                email_token INT NOT NULL CHECK (email_token BETWEEN 100000 AND 999999),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_disabled BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (userID) REFERENCES Users(userID)
            );

            """)

            await cursor.execute("""
            CREATE TABLE IF NOT EXISTS pass_reset (
                tokenID INT AUTO_INCREMENT PRIMARY KEY,
                reset_token VARCHAR(128),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                userID INT,
                FOREIGN KEY (userID) REFERENCES users(userID)
            );
            """)

            await cursor.execute("""
            CREATE TABLE IF NOT EXISTS Chats (
                chatID INT AUTO_INCREMENT PRIMARY KEY,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                type ENUM('group', 'private') DEFAULT 'private',
                last_message DATETIME DEFAULT CURRENT_TIMESTAMP,
                testing_chat_caract VARCHAR(20) UNIQUE
            );
            """)
            await cursor.execute("""
            CREATE TABLE IF NOT EXISTS Participants (
                chatID INT,
                userID INT,
                FOREIGN KEY (chatID) REFERENCES Chats(chatID) ON DELETE CASCADE,
                FOREIGN KEY (userID) REFERENCES Users(userID) ON DELETE CASCADE,
                PRIMARY KEY (chatID, userID)
            );
            """)
            await cursor.execute("""
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

            # Create MySQL user and grant privileges
            await cursor.execute(f"""
            CREATE USER IF NOT EXISTS '{db_config["user"]}'@'localhost' IDENTIFIED WITH caching_sha2_password BY 'S3cret#Code1234';
            """)
            await cursor.execute(f"""
            GRANT SELECT, INSERT, UPDATE, DELETE ON {db_config['db']}.* TO '{db_config["user"]}'@'localhost';
            """)

            await conn.commit()
            print("Database setup complete.")
    except aiomysql.Error as err:
        print(f"Error: {err}")
    finally:
        conn.close()

def start_servers():
    try:
        subprocess.Popen(
            ["cmd.exe", "/c", "start", "WebSocket Server", "python", "server_ws.py"],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        subprocess.Popen(
            ["cmd.exe", "/c", "start", "Flask Server", "python", "server_flask.py"],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    except Exception as e:
        print(f"Error starting servers: {e}")

# Run the async database setup and start servers
if __name__ == "__main__":
    asyncio.run(setup_database())
    start_servers()
