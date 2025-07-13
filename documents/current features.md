## ✅ Current Features – Beta GUI Release

### 🧑‍💼 Account & Identity

* **User Registration**: Sign up with username, password, and email.
* **Email Verification**: Email-based token verification after registration.
* **Login & Token-Based Auth**: Secure login using access and refresh tokens.
* **Password Reset**: Request password reset via email using a verification link.
* **Session Persistence**: Secure storage and reuse of session and refresh tokens.
* **Logout**: Clears all tokens and redirects to login screen.

### 💬 Messaging System

* **One-on-One Messaging**: Initiate chats with individual users by username.
* **Real-Time Messaging**: Instant communication using WebSocket protocol.
* **Typing Indicator**: Notifies when the other user is typing.
* **Message History**: Load and display full chat history upon selecting a chat.
* **Delete Conversations**: Remove chats from your sidebar via a modal confirmation.

### 👤 User Status & Presence

* **Live Online Status**: Real-time updates of user presence (online/offline) through WebSocket events.
* **Visual Indicators**: Color-coded dots and tooltip text to indicate status next to usernames in the chat list.

### 🌐 Server Connection Handling

* **Live Server Status Checks**: Automatically detects and displays if the backend is online.
* **Offline Handling**: Disables buttons and actions when the server is unreachable.
* **Retry Mechanism**: Automatic retry or manual retry button for reconnecting.

### 🖥️ Graphical User Interface (Electron)

* **Multi-Page SPA**: Includes welcome, login, register, reset-password, email verification, and main chat interface.
* **Two-Pane Layout**: Sidebar for chat list + user panel, and main chat window with input and message history.
* **Modern Dark Theme**: Fully themed interface with responsive design and visual polish.
* **Toast Notifications**: Contextual feedback for actions, errors, and success states.
* **Keyboard UX**: Send with Enter, add newlines with Shift+Enter.

### 🧩 Architecture & Extensibility

* **Modular Codebase**: Separation of HTML/CSS/JS with clear logic boundaries.
* **API Layer**: Centralized wrapper for all server requests, with auth/session management.
* **Secure Local Storage**: Credentials stored and accessed through a secure store.