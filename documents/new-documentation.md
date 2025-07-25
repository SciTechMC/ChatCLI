## Table of Contents

1. [HTTP API Endpoints](#http-api-endpoints)

   * [Base Routes](#base-routes)
   * [User Routes](#user-routes)
   * [Chat Routes](#chat-routes)
2. [WebSocket API](#websocket-api)

## HTTP API Endpoints

* fortbow.zapto.org:5123
* fortbow.zapto.org:8765

### Base Routes

<aside>
These routes handle generic pages and server connectivity.
</aside>

#### `GET /`

* **Description**: Renders the welcome page.
* **Response**: HTML content.

#### `GET, POST /verify-connection`

* **Description**: Checks server connectivity.
* **Response**:

  * `200 OK` with JSON `{ "status": "ok", "message": "", "response": "Server is reachable!" }`

#### `GET, POST /subscribe`

* **Description**: Subscribes an email address to notifications.
* **Request (POST)**: Form data

  ```
  email=user@example.com
  ```
* **Response**:

  * `200 OK` with confirmation HTML or flash message.
  * `400 Bad Request` for invalid or missing email.

---

### User Routes

<aside>
User management: registration, email verification, login, password reset, and token refresh.
</aside>

#### `POST /user/register`

* **Description**: Registers a new user and sends a verification code.
* **Request Body**:

  ```json
  {
    "username": "string",
    "email": "string",
    "password": "string"
  }
  ```
* **Response**:

  * `200 OK` with JSON `{ "status": "ok", "message": "", "response": "Verification email sent!" }`
  * `400 Bad Request` for invalid input or existing user.

#### `POST /user/verify-email`

* **Description**: Verifies a user's email using a code.
* **Request Body**:

  ```json
  {
    "username": "string",
    "email_token": "string"
  }
  ```
* **Response**:

  * `200 OK` with JSON `{ "status": "ok", "message": "", "response": "Email verified!" }`
  * `400 Bad Request` for invalid or expired code.

#### `POST /user/login`

* **Description**: Authenticates a user and issues access and refresh tokens.
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
      "message": "Login successful",
      "response": "",
      "access_token": "<access_token>",
      "refresh_token": "<refresh_token>"
    }
    ```
  * `400 Bad Request` or `404 Not Found` for invalid credentials.

#### `GET /user/refresh-token`

* **Description**: Rotates a valid refresh token and issues new tokens.
* **Request Body** (JSON):

  ```json
  {
    "refresh_token": "string"
  }
  ```
* **Response**:

  * `200 OK` with JSON:

    ```json
    {
      "status": "ok",
      "message": "Token refreshed",
      "response": "",
      "access_token": "<new_access_token>",
      "refresh_token": "<new_refresh_token>"
    }
    ```
  * `401 Unauthorized` for invalid or expired token.

#### `POST /user/reset-password-request`

* **Description**: Initiates a password reset by emailing a reset link.
* **Request Body**:

  ```json
  {
    "username": "string"
  }
  ```
* **Response**:

  * `200 OK` with JSON `{ "status": "ok", "message": "", "response": "Password reset email sent!" }`
  * `404 Not Found` if user not found.

#### `GET, POST /user/reset-password`

* **Description**: Completes password reset using a token.
* **Query Parameters** (GET): `?token=<reset_token>&username=<username>`
* **Request Body** (POST): Form data

  ```
  password=newpassword
  confirm_password=newpassword
  ```
* **Response**:

  * `200 OK` with JSON `{ "message": "Password reset successfully" }`
  * `400 Bad Request` for invalid/expired token or weak password.

---

### Chat Routes

<aside>
REST API for creating and retrieving chat data.
</aside>

All chat routes require a valid session token in the request body.

#### `GET /chat/`

* **Description**: Returns a simple index message.
* **Response**: `200 OK`, body: `"chat's index route"`

#### `POST /chat/fetch-chats`

* **Description**: Retrieves a list of chat participants for the user.
* **Request Body**:

  ```json
  {
    "session_token": "string"
  }
  ```
* **Response**:

  * `200 OK` with JSON:

    ```json
    {
      "status": "ok",
      "response": [
        { "chatID": 123, "name": "otheruser" }
      ]
    }
    ```

#### `POST /chat/create-chat`

* **Description**: Creates a new chat between two users.
* **Request Body**:

  ```json
  {
    "receiver": "username",
    "session_token": "string"
  }
  ```
* **Response**:

  * `200 OK` with JSON `{ "status": "ok", "message": "", "response": "Chat created successfully!" }`
  * `400 Bad Request` or `409 Conflict` for invalid input or duplicate chat.

#### `POST /chat/messages`

* **Description**: Fetches messages for a given chat.
* **Request Body**:

  ```json
  {
    "username": "string",
    "session_token": "string",
    "chatID": 123,
    "limit": 50
  }
  ```
* **Response**:

  * `200 OK` with JSON array of message objects:

    ```json
    [
      {
        "messageID": 1,
        "userID": 2,
        "username": "sender",
        "message": "Hello",
        "timestamp": "ISO8601"
      }
    ]
    ```

#### `POST /chat/delete-chat`

* **Description**: Removes the user from the specified chat. If no participants remain, deletes the chat and its messages.
* **Request Body** (JSON):

  ```json
  {
    "session_token": "string",
    "chatID": 123
  }
  ```
* **Response**:

  * `200 OK` with JSON `{ "status": "ok", "message": "", "response": "Chat deleted successfully!" }`
  * `400 Bad Request`, `401 Unauthorized`, `404 Not Found`, or `500 Internal Server Error` for errors.

---

## WebSocket API

The WebSocket endpoint enables real-time chat. Connect to:

```
wss://ws.chat.puam.be/ws
```

### 1. Connection & Authentication

**Client:** After connecting, send an auth message:

```json
{
  "type": "auth",
  "token": "<session_token>"
}
```

**Server:** Replies:

```json
{ "type": "auth_ack", "status": "ok" }
```

On failure, the connection is closed.

---

### 2. Actions

After authentication, send JSON messages with a `type` field. Supported types:

| Type         | Payload Fields                | Description                |
| ------------ | ----------------------------- | -------------------------- |
| `join_chat`  | `chatID`: int                 | Join a chat room           |
| `leave_chat` | `chatID`: int                 | Leave a chat room          |
| `post_msg`   | `chatID`: int, `text`: string | Send a message to the chat |

#### Example: Join Chat

```json
{ "type": "join_chat", "chatID": 123 }
```

#### Example: Leave Chat

```json
{ "type": "leave_chat", "chatID": 123 }
```

#### Example: Send Message

```json
{ "type": "post_msg", "chatID": 123, "text": "Hello everyone!" }
```

If an unknown action is sent, the server replies:

```json
{
  "type": "error",
  "message": "Unknown action: <type>"
}
```

---

### 3. Server Broadcasts

Whenever a message is posted, the server broadcasts to all subscribers of the chat:

```json
{
  "type": "new_message",
  "messageID": 1,
  "chatID": 123,
  "userID": 2,
  "username": "sender",
  "message": "Hello everyone!",
  "timestamp": "2025-06-27T12:34:56Z"
}
```

---

**Note:**

* All chat actions require a valid authenticated WebSocket session.
* The server automatically manages chat subscriptions and cleans up on disconnect.
