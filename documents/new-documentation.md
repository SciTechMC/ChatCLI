**API Documentation**

## Table of Contents

1. [HTTP API Endpoints](#http-api-endpoints)

   * [Base Routes](#base-routes)
   * [User Routes](#user-routes)
   * [Chat Routes](#chat-routes)
2. [WebSocket API](#websocket-api)

## HTTP API Endpoints

### Base Routes

<aside>
These routes handle generic pages and server connectivity.
</aside>

#### `GET /`

* **Description**: Renders the welcome page.
* **Response**: HTML content.

#### `GET, POST /verify-connection`

* **Description**: Checks server connectivity and client compatibility.
* **Request (POST)**:

  ```json
  {
    "version": "electron_app"  // or other client version strings
  }
  ```
* **Response**:

  * `200 OK` with JSON `{"status": "ok", "message": "Hello World!"}` on success.
  * `400 Bad Request` on missing/invalid JSON or incompatible version.

#### `GET, POST /subscribe`

* **Description**: Subscribes an email address to notifications.
* **Request (POST)**:

  ```json
  {
    "email": "user@example.com"
  }
  ```
* **Response**:

  * `200 OK` with confirmation HTML.
  * `400 Bad Request` for invalid or missing email.

---

### User Routes

<aside>
User management: registration, email verification, login, and password reset.
</aside>

#### `POST /user/register`

* **Description**: Registers a new user.
* **Request Body**:

  ```json
  {
    "username": "string",  // unique
    "email": "string",     // valid email
    "password": "string"   // plain-text, will be hashed
  }
  ```
* **Response**:

  * `201 Created` with JSON `{ "status": "ok", "message": "Registration successful. Verification email sent." }`
  * `400 Bad Request` if email/username invalid or already exists.

#### `POST /user/verify-email`

* **Description**: Verifies a user's email using a token.
* **Request Body**:

  ```json
  {
    "token": "string"      // emailed token
  }
  ```
* **Response**:

  * `200 OK` with JSON `{ "status": "ok", "message": "Email verified." }`
  * `400 Bad Request` for invalid or expired token.

#### `POST /user/login`

* **Description**: Authenticates a user and issues a session token.
* **Request Body**:

  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```
* **Response**:

  * `200 OK` with JSON:

    ```json
    {
      "status": "ok",
      "token": "<session_token>",
      "expires_in": 3600  // seconds
    }
    ```
  * `401 Unauthorized` for invalid credentials.

#### `POST /user/reset-password-request`

* **Description**: Initiates a password reset by emailing a reset link.
* **Request Body**:

  ```json
  { "email": "user@example.com" }
  ```
* **Response**:

  * `200 OK` with JSON `{ "status": "ok", "message": "Password reset link sent." }`
  * `404 Not Found` if email not registered.

#### `GET, POST /user/reset-password`

* **Description**: Completes password reset using a token.
* **Query Parameters** (for GET): `?token=<reset_token>`
* **Request Body** (POST):

  ```json
  {
    "token": "string",
    "new_password": "string"
  }
  ```
* **Response**:

  * `200 OK` with JSON `{ "status": "ok", "message": "Password has been reset." }`
  * `400 Bad Request` for invalid/expired token or weak password.

---

### Chat Routes

<aside>
REST API for creating and retrieving chat data.
</aside>

All chat routes require a valid session token in the `Authorization` header.

#### `GET /chat/`

* **Description**: Returns a simple index message.
* **Response**: `200 OK`, body: `"chat's index route"`

#### `POST /chat/fetch-chats`

* **Description**: Retrieves a list of chats the user participates in.
* **Request Body**:

  ```json
  {
    "username": "string"
  }
  ```
* **Response**:

  * `200 OK` with JSON array:

    ```json
    [
      { "chatID": 1, "participants": ["alice", "bob"], "last_message": "...", "updated_at": "ISO8601" },
      // ...
    ]
    ```

#### `POST /chat/create-chat`

* **Description**: Creates a new chat between participants.
* **Request Body**:

  ```json
  {
    "participants": ["alice", "bob", ...]
  }
  ```
* **Response**:

  * `201 Created` with JSON `{ "chatID": 123, "participants": [...], "created_at": "ISO8601" }`
  * `400 Bad Request` for invalid input.

#### `POST /chat/messages`

* **Description**: Fetches messages for a given chat.
* **Request Body**:

  ```json
  {
    "chatID": 123,
    "limit": 50,           // optional, default 100
    "order": "ASC"       // or "DESC"
  }
  ```
* **Response**:

  * `200 OK` with JSON array of message objects:

    ```json
    [
      { "messageID": 1, "chatID": 123, "sender": "alice", "text": "Hello", "sent_at": "ISO8601" },
      // ...
    ]
    ```

---

## WebSocket API

The WebSocket endpoint enables real-time chat. Connect to:

```
wss://api.example.com/ws/chat
```

### 1. Connection & Authentication

* **Client**: After connecting, send an auth message:

  ```json
  {
    "type": "auth",
    "username": "alice",
    "session_token": "<token>"
  }
  ```
* **Server**: Replies:

  ```json
  { "type": "auth_ack", "status": "ok" }
  ```

  On failure, the connection is closed.

### 2. Actions

Subsequent messages must include a `type` field:

| Type      | Payload Fields                | Description                |
| --------- | ----------------------------- | -------------------------- |
| `join`    | `chatID`: int                 | Join a chat room           |
| `leave`   | `chatID`: int                 | Leave a chat room          |
| `message` | `chatID`: int, `text`: string | Send a message to the chat |

#### Example: Join Chat

```json
{ "type": "join", "chatID": 123 }
```

#### Example: Send Message

```json
{ "type": "message", "chatID": 123, "text": "Hello everyone!" }
```

### 3. Server Broadcasts

Whenever a message is posted, the server broadcasts:

```json
{
  "type": "message",
  "username": "alice",
  "chatID": 123,
  "text": "Hello everyone!",
  "sent_at": "2025-06-27T12:34:56Z"
}
```