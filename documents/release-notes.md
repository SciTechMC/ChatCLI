🚀 ChatCLI 0.1.0 Beta Release
Welcome to the **first Beta release** of ChatCLI!

This version represents a significant milestone with the introduction of a fully functional **Graphical User Interface (GUI)** using Electron, modular backend integration, and substantial improvements in usability, security, and performance.

---

## 🌟 Features

### 🖥️ Graphical User Interface (NEW)

* Full dark-themed, responsive Electron app
* Dual-pane layout: Chat list + real-time messaging window
* Toast notifications, typing indicators, and real-time presence

### 🧑‍💼 User Management

* Secure registration, login, and logout
* Persistent login via secure token storage
* Email verification system via token
* Password reset via email

### 💬 Messaging

* One-on-one chat creation
* Real-time encrypted messaging via WebSocket
* View and manage chat history
* Typing indicator and user presence status
* Chat deletion with confirmation modal

### 🧩 Architecture

* Modularized client-server structure
* Improved API abstraction (via `api.js`)
* WebSocket + HTTP hybrid model
* Secure session & refresh token handling

### 🎨 UI/UX

* Redesigned styles with modern, accessible dark theme
* Keyboard shortcuts: Enter to send, Shift+Enter for newline
* Real-time server status detection and feedback

---

## 🐛 Known Issues (Beta Phase)

*These will be addressed in upcoming Beta updates.*

* Group chats are not yet implemented
* No in-app profile or friend system UI
* No message editing or deletion yet
* No offline support or caching
* Performance may vary with large message histories
* When deleting a chat, it will stay in the UI until the user has reloaded the app (control+R)

---

## 🧪 How to Try the Beta

To participate in beta testing:

1. Download and install the latest version of **ChatCLI.exe**
2. Launch the Electron GUI app
3. Register a user and verify via email
4. Login, create chats, and send messages
5. Try deleting a chat and starting a new one
6. Test password reset flow via the login screen

📎 Download the setup .exe from down below

📝 Share bugs, ideas, and feedback on the [GitHub Issues](#) page.

---

## 🛠 Major Changes Since 0.2.0 Alpha

### 🔧 Backend Improvements

* Token-based session and refresh flow
* Modular backend calls for authentication, chat, and messaging
* RESTful route structure and fully updated API documentation

### 🚀 Client Improvements

* Brand-new Electron GUI replacing CLI
* Secure credential storage using Electron `secureStore`
* Unified notification system and real-time WebSocket integration
* Automatic handling of server connection and token refresh

### 🧼 Fixed Alpha Bugs

* ✅ Multi-line message input now supported via Shift+Enter
* ✅ Startup delay resolved; no need to click + press Enter
* ✅ Chat window freezing on invalid click has been fixed

---

⚠️ **Security Notice**
All messages are encrypted during transit. However, do not send personal or sensitive data.

⚠️ **Beta Data Warning**
Messages and user data may be cleared between releases. This is a testing phase.

---

## 📌 Want Release Notifications?

Subscribe on [this website](http://fortbow.zapto.org:5123/subscribe)