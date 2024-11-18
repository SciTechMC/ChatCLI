ChatCLI - A Command-Line Chat System

ChatCLI is a lightweight, terminal-based chat application inspired by the simplicity of WhatsApp and Discord Direct Messaging. Designed without a GUI, ChatCLI allows users to experience seamless, real-time communication in a command-line environment.

Features

User Authentication: Simple sign-up and log-in system.

Direct Messaging: Real-time message exchange between users.

Conversation History: Access and review past conversations with other users.


Built for simplicity, ChatCLI focuses on essential chat functionalities, making it an ideal foundation for a more extensive messaging application.

---

# **ChatCLI Code Documentation**

---

# Client

### **Imports**

#### **1. Standard Library Imports**
- **`sys`**  
  - Provides system-specific parameters and functions, such as exiting the application (`sys.exit()`).
- **`os`**  
  - Interacts with the operating system.  
  - Example: Ensures the saved login directory exists with `os.makedirs(saved_login_dir)`.
- **`time`**  
  - Manages delays (e.g., `time.sleep(10)` for periodic message retrieval).
- **`multiprocessing`**  
  - Enables concurrent task execution (e.g., running `retrieve_messages` in a separate process).
- **`datetime.date`**  
  - Gets the current date for logging or display purposes.  

#### **2. Third-Party Library Imports**
- **`requests`**  
  - Handles HTTP requests such as login, registration, and retrieving chats.  
  - Example: `requests.post(login_url, data={"username": username, "password": password})`.
- **`flask.jsonify`**  
  - Converts Python dictionaries to JSON responses for server communication.  
  - Example: `jsonify({"message": "Welcome to ChatCLI"})`.
- **`rich.print`**  
  - Provides styled and colorized terminal outputs.  
  - Example: Displaying prompts or errors in a visually appealing manner.

#### **Notes**
Ensure all third-party libraries are installed:
```bash
pip install requests flask rich
```

---

### **Global Variables**

- **`server_config`**: Stores server endpoints like `login_url`, `register_url`, etc.  
- **`username`**: The currently logged-in username.  
- **`password`**: The user's password for authentication.  
- **`receiver`**: The recipient in the current chat session.  
- **`key`**: Session key returned after login.  
- **`saved_login_dir`**: Path for saving login credentials locally.  
- **`current_date`**: Current date in `YYYY-MM-DD` format.

---

### **Homepage Navigation**

#### **`homepage()`**

Displays the main menu for navigating between actions:
1. Register  
2. Log In  
3. Exit  
4. Conversations (if logged in).

- **Input**: User selection (1-4).
- **Output**: Calls functions based on selection.  
  Example: `"1"` triggers the `register()` function.  

---

### **Client Startup**

#### **`start_client()`**

Initializes the client and attempts to connect to the server.

- **Workflow**:  
  1. Iterates through possible server URLs.
  2. Uses `check_server_connection()` to validate connectivity.
  3. Configures server endpoints with `configure_urls()` if successful.
  4. Navigates to `homepage()` or retries connection if all attempts fail.

- **Example Execution**:  
  ```plaintext
  Connecting to server...
  Connected to http://127.0.0.1:5000
  ```
  
---

### **Server Connection Utilities**

#### **`check_server_connection(possible_server_urls, client_version)`**

Tests server URLs for compatibility.

- **Input**: List of URLs and client version.
- **Output**: The first compatible server URL or `None`.  
- **Request Example**:  
  ```json
  {"message": "Hello?"}
  ```
- **Response Example**:  
  ```json
  {"server_version": "pre-alpha V0.9.0"}
  ```

#### **`configure_urls(base_url)`**

Generates URLs for server endpoints based on the base URL.

- **Input**: `base_url = "http://127.0.0.1:5000"`.
- **Output**: Dictionary with endpoints such as `send_url`, `login_url`, etc.

---

### **Login and Registration**

#### **`register()`**

Handles user registration.

- **Input**: Username and password.  
- **Request**:  
  ```json
  {"username": "JohnDoe", "password": "password123"}
  ```
- **Response Example**:  
  - Success: `"User has been registered!"`  
  - Failure: `"Username already exists"`.

#### **`login()`**

Authenticates the user.

- **Input**: Username and password.  
- **Request**:  
  ```json
  {"username": "JohnDoe", "password": "password123"}
  ```
- **Response Example**:  
  ```json
  {"key": "a1b2c3d4"}
  ```

#### **`login_procedure()`**

Prompts the user to use saved credentials or input them manually.

#### **`save_login()`**

Saves credentials locally in the `saved_login_dir`.

- **File Example**:  
  - `JohnDoe.txt` containing `JohnDoe,password123`.

#### **`check_saved_login()`**

Checks if credentials exist in the saved login directory.

---

### **Conversations and Chat Handling**

#### **`conversations()`**

Displays a list of active chats or starts a new one.

- **Request Example**:  
  ```json
  {"username": "JohnDoe", "key": "a1b2c3d4"}
  ```
- **Response Example**:  
  ```json
  {
      "chats": [
          {"users": "JohnDoe,JaneDoe", "last_used": "2024-11-18"}
      ]
  }
  ```

#### **`choose_chat(chats, indexed, choice)`**

Opens a selected chat by its index.

#### **`choose_chat_by_name(indexed, choice)`**

Opens a chat by the recipient's username.

#### **`start_chatting()`**

Begins real-time chat in a multiprocessing setup.

- **Request Example**:  
  ```json
  {"sender": "JohnDoe", "receiver": "JaneDoe", "message": "Hello!"}
  ```

#### **`retrieve_messages(open_chat_url, user, receive)`**

Continuously fetches new messages in the active chat.

- **Request Example**:  
  ```json
  {"users": "JohnDoe,JaneDoe"}
  ```
- **Response Example**:  
  ```json
  {
      "chat": {
          "Hello!": {"from": "JaneDoe", "datetime": "2024-11-18T10:00:00"},
          "Hi!": {"from": "JohnDoe", "datetime": "2024-11-18T10:01:00"}
      }
  }
  ```

#### **`check_user_server()`**

Validates if a recipient exists on the server.

- **Request Example**:  
  ```json
  {"username": "JaneDoe"}
  ```

---

### **Program Entry Point**

#### **`__main__`**

Starts the application by invoking `start_client()`.

---

# Server

### **Imports**

#### **1. Standard Library Imports**
- **`random`**  
  - Generates secure session keys for users.  
  - Example: `random.SystemRandom().choice(string.ascii_uppercase + string.digits)` generates random characters.

- **`string`**  
  - Provides string constants such as uppercase letters and digits.  

- **`os`**  
  - Handles file and directory operations like creating folders or checking file existence.  
  - Example: `os.makedirs("connection-checks", exist_ok=True)` ensures a directory exists.

- **`json`**  
  - Reads and writes JSON data to/from files.  
  - Example: `json.dump(data, chatsfile, indent=4)` saves data in a human-readable JSON format.

- **`datetime.date`**  
  - Captures the current date for timestamps in logs.  

- **`datetime.datetime`**  
  - Captures the precise current date and time.  

#### **2. Third-Party Library Imports**
- **`Flask`**  
  - Framework for creating and managing server routes and endpoints.  
  - Example: `@app.route("/check-connection")` defines the `/check-connection` endpoint.

- **`Flask.request`**  
  - Handles incoming HTTP requests and retrieves JSON payloads.  
  - Example: `request.get_json()` fetches JSON data from a POST request.  

- **`Flask.jsonify`**  
  - Converts Python objects into JSON responses for clients.  
  - Example: `return jsonify({"status": "Hello World"})`.

- **`rich.print`**  
  - Provides styled output for server logs.  
  - Example: `print(f"[red]SERVER VERSION: {server_version}[/]")`.

- **`requests`**  
  - Enables HTTP requests to external APIs, like user existence checks.  
  - Example: `requests.post("http://127.0.0.1:5000/check-user-exists")`.

---

### **Global Variables**
- **`server_version`**: Identifies the current server version.  
- **`app`**: The Flask application instance that defines server behavior.  

---

### **Routes and Endpoints**

#### **1. `/check-connection`**
- **Description**: Validates the client-server connection.  
- **Method(s)**: `GET`, `POST`.  
- **Workflow**:
  - Logs the IP address and timestamp of each client connection.
  - Responds with server version if the message `"Hello?"` is received.
- **Responses**:  
  - **`200 OK`**: If the connection is valid.  
    ```json
    {"status": "Hello World", "server_version": "pre-alpha V0.9.0"}
    ```
  - **`400 Bad Request`**: For invalid messages.  

#### **2. `/open-convo`**
- **Description**: Retrieves chat history between two users.  
- **Method(s)**: `GET`, `POST`.  
- **Workflow**:
  - Checks for a chat file corresponding to the provided users.
  - Reads the chat data from the file if it exists.
- **Responses**:  
  - **`200 OK`**: Returns the chat data.  
    ```json
    {"chat": {"Hello!": {"from": "JaneDoe", "datetime": "2024-11-18"}}}
    ```
  - **`400 Bad Request`**: If no chat is found or the data is invalid.  

#### **3. `/initiate-conversation`**
- **Description**: Initiates a new chat session between users.  
- **Method(s)**: `GET`, `POST`.  
- **Workflow**:
  - Checks if the receiver exists using `/check-user-exists`.
  - Creates or updates chat metadata in `chats.json`.
  - Generates a chat file for the users with a welcome message if one does not already exist.
- **Responses**:  
  - **`200 OK`**: On successful chat initiation.  
  - **`400 Bad Request`**: If the receiver does not exist or the chat already exists.  

#### **4. `/send`**
- **Description**: Sends a message between users and updates the chat file.  
- **Method(s)**: `GET`, `POST`.  
- **Workflow**:
  - Validates the chat file for the sender-receiver pair.
  - Appends the new message to the chat history.
- **Responses**:  
  - **`200 OK`**: On successful message delivery.  
  - **`400 Bad Request`**: For invalid data or missing chat files.  

#### **5. `/login`**
- **Description**: Authenticates a user and generates a session key.  
- **Method(s)**: `GET`, `POST`.  
- **Workflow**:
  - Verifies username and password against stored credentials.
  - Creates a session key upon successful login and saves it in `keys.json`.
- **Responses**:  
  - **`200 OK`**: On successful login with session key.  
    ```json
    {"status": "Login successful!", "key": "A1B2C3D4"}
    ```
  - **`400 Bad Request`**: For invalid credentials or data.  

#### **6. `/register`**
- **Description**: Registers a new user with a username and password.  
- **Method(s)**: `GET`, `POST`.  
- **Workflow**:
  - Saves the username and password in a text file.
  - Prevents duplicate usernames.  
- **Responses**:  
  - **`200 OK`**: On successful registration.  
  - **`400 Bad Request`**: If the username is already taken.  

#### **7. `/convo`**
- **Description**: Retrieves all conversations for a user.  
- **Method(s)**: `GET`, `POST`.  
- **Workflow**:
  - Searches `chats.json` for all chats involving the given username.
- **Responses**:  
  - **`200 OK`**: Returns a list of conversations.  
  - **`401 Unauthorized`**: If no conversations are found.  

#### **8. `/check-user-exists`**
- **Description**: Checks if a user exists in the database.  
- **Method(s)**: `GET`, `POST`.  
- **Workflow**:
  - Validates the existence of a user file corresponding to the username.
- **Responses**:  
  - **`200 OK`**: If the user exists.  
  - **`400 Bad Request`**: If the user does not exist.  

---

### **Helper Functions**

#### **1. `save_key(username, key)`**
- **Description**: Saves a user's session key to `keys.json`.  
- **Workflow**:
  - Loads existing keys, or starts with an empty dictionary if the file is missing or corrupted.
  - Updates the dictionary with the new key and writes it back to the file.

---

### **Server Initialization**

#### **`__main__`**
- **Description**: Entry point of the server. Starts the Flask app.  
- **Example Output**:  
  ```plaintext
  * SERVER VERSION: pre-alpha V0.9.0
  ```  
  Runs the app on `0.0.0.0` with debugging enabled.  