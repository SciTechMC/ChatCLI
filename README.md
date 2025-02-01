ChatCLI - A Command-Line Chat System

ChatCLI is a lightweight, terminal-based chat application inspired by the simplicity of WhatsApp and Discord Direct Messaging. Designed without a GUI, ChatCLI allows users to experience seamless, real-time communication in a command-line environment.
---
# When preping for release
- Change database used in all server files (server_flask/ws, init server) from **db_env.dev()** to **db_env.prod()** (this should only be one line per file)
- Remove production or dev question at the start of server_flask file
- Build both client files
