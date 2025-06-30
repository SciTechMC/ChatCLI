// renderer-main.js
document.addEventListener('DOMContentLoaded', async () => {
  const chatListEl  = document.getElementById('chat-list');
  const messagesEl  = document.getElementById('messages');
  const formEl      = document.getElementById('chat-form');
  const inputEl     = document.getElementById('chat-message');
  const logoutBtn   = document.getElementById('logout-btn');
  const profileEl   = document.getElementById('profile-username');

  // 1️⃣ Auto-login with stored refresh token
  const storedRefresh = await window.secureStore.get('refresh_token');
  if (storedRefresh) {
    try {
      // Refresh session
      const refreshRes = await window.api.refreshToken();
      // Persist new refresh token
      await window.secureStore.set('refresh_token', refreshRes.refresh_token);
      // Update in-memory session token
      window.api.setSessionToken(refreshRes.token);
      // Show username
      profileEl.textContent = refreshRes.username;
    } catch {
      // Invalid/expired → clear and go to login
      await window.secureStore.delete('refresh_token');
      return void (location.href = 'login.html');
    }
  } else {
    // No token → redirect to login
    return void (location.href = 'login.html');
  }

  // 2️⃣ Fetch and render chats
  try {
    const chats = await window.api.fetchChats(profileEl.textContent);
    chats.forEach(chat => {
      const btn = document.createElement('button');
      btn.classList.add('chat-list-item');
      btn.textContent = chat.participants.join(', ');
      btn.addEventListener('click', () => selectChat(chat.chatID));
      chatListEl.appendChild(btn);
    });
  } catch (err) {
    console.error('[main] fetchChats error', err);
  }

  // 3️⃣ Open WebSocket & authenticate
  const ws = new WebSocket('ws://127.0.0.1:8765/ws');
  ws.addEventListener('open', () => {
    ws.send(JSON.stringify({
      type: 'auth',
      token: window.api.getSessionToken(), // documentation expects 'token'
    }));
  });

  ws.addEventListener('message', evt => {
    try {
      const msg = JSON.parse(evt.data);
      if (msg.type === 'new_message') {
        appendMessage(msg.userID, msg.message); // userID is numeric, you may want to map to username
      }
    } catch (err) {
      console.error('[main] WS parse error', err);
    }
  });

  let currentChatID = null;
  function selectChat(chatID) {
    currentChatID = chatID;
    // Clear old messages
    messagesEl.innerHTML = '';
    // Fetch history
    window.api.fetchMessages(chatID, 100, 'ASC')
      .then(msgs => msgs.forEach(m => appendMessage(m.sender, m.text)))
      .catch(err => console.error('[main] fetchMessages error', err));
    // Join the chat room
    ws.send(JSON.stringify({ type: 'join_chat', chatID })); // use 'join_chat'
  }

  function appendMessage(sender, text) {
    const m = document.createElement('div');
    m.classList.add('message');
    m.textContent = `${sender}: ${text}`;
    messagesEl.appendChild(m);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // 4️⃣ Sending messages
  formEl.addEventListener('submit', e => {
    e.preventDefault();
    const text = inputEl.value.trim();
    if (!text || currentChatID === null) {
      return;
    }
    ws.send(JSON.stringify({
      type:   'post_msg', // <-- match your backend
      chatID: currentChatID,
      text,
    }));
    inputEl.value = '';
  });

  // 5️⃣ Logout
  logoutBtn.addEventListener('click', async () => {
    await window.secureStore.delete('refresh_token');
    location.href = 'login.html';
  });
});
