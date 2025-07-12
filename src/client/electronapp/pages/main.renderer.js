// main.renderer.js

const ip = "ws://fortbow.zapto.org:8765/ws";

document.addEventListener('DOMContentLoaded', async () => {
  // 1) Get stored credentials
  const token    = await window.secureStore.get('session_token');
  const username = await window.secureStore.get('username');
  if (!token || !username) {
    return void (location.href = 'login.html');
  }

  // Username display
  const userInfoEl = document.getElementById('user-info');
  if (userInfoEl) {
    userInfoEl.textContent = username;
    userInfoEl.style.wordBreak = 'break-all';
    userInfoEl.style.fontWeight = 'bold';
    userInfoEl.style.fontSize = '1.1em';
    userInfoEl.style.marginBottom = '16px';
    userInfoEl.style.maxWidth = '100%';
    userInfoEl.style.overflowWrap = 'break-word';
    userInfoEl.style.textAlign = 'center';
    userInfoEl.style.padding = '8px 0';
    userInfoEl.style.color = 'var(--text-secondary)';
  }

  // 2) Cache DOM elements
  const chatListEl    = document.getElementById('chat-list');
  const messagesEl    = document.getElementById('messages');
  const newChatInput  = document.getElementById('new-chat-username');
  const createChatBtn = document.getElementById('create-chat-btn');
  const messageInput  = document.getElementById('message-text');
  const sendBtn       = document.getElementById('send-btn');
  const logoutBtn     = document.getElementById('logout-btn');

  let currentChatID = null;
  let ws;

  // 3) Open & auth WebSocket
  function connectWS() {
    ws = new WebSocket(ip);
    ws.addEventListener('open', () => {
      ws.send(JSON.stringify({ type: 'auth', token }));
    });
    ws.addEventListener('message', ({ data }) => {
      const msg = JSON.parse(data);
      if (msg.type === 'new_message' && msg.chatID === currentChatID) {
        appendMessage(msg);
      }
      if (msg.type === "user_typing" && msg.chatID === currentChatID && msg.username !== username) {
        const typingEl = document.getElementById('typing-indicator');
        typingEl.textContent = `${msg.username} is typing...`;
        typingEl.style.display = 'block';
        clearTimeout(typingEl._timeout);
        typingEl._timeout = setTimeout(() => typingEl.style.display = 'none', 3000);
      }
      if (msg.type === "user_status") {
        const chatItems = document.querySelectorAll(`[data-username="${msg.username}"]`);
        chatItems.forEach(el => {
          el.classList.toggle("online", msg.online);
        });
      }  
    });
    ws.addEventListener('close', () => setTimeout(connectWS, 2000));
  }
  connectWS();

  // 4) Load chat list (HTTP)
  async function loadChats() {
    try {
      const res = await window.api.request('/chat/fetch-chats', {
        body: JSON.stringify({ session_token: token })
      });
      const chats = Array.isArray(res.response) ? res.response : [];
      chatListEl.innerHTML = '';
      chats.forEach(({ chatID, name }) => {
        const li = document.createElement('li');
        li.textContent = name;
        li.dataset.chatId = chatID;
        li.dataset.username = name; // <== Enables us to target this later
        li.classList.add('chat-entry'); // Optional class for styling

        // Add delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Delete';
        deleteBtn.className = 'delete-chat-btn';
        deleteBtn.onclick = () => deleteChat(chatID);

        li.appendChild(deleteBtn);
        li.onclick = () => selectChat(chatID);
        chatListEl.appendChild(li);
      });
    } catch (err) {
      console.error('loadChats error', err);
    }
  }
  loadChats();

  // Add deleteChat function
  async function deleteChat(chatID) {
    console.log('Deleting chat with ID:', chatID); // Debugging
    if (!confirm('Are you sure you want to delete this chat?')) return;

    try {
      await window.api.request('/chat/delete-chat', {
        body: JSON.stringify({ session_token: token, chatID })
      });
      alert('Chat deleted successfully!');
      await loadChats(); // Reload the chat list
    } catch (err) {
      console.error('deleteChat error', err);
      alert('Could not delete chat: ' + (err.message || err));
    }
  }

  // 5) Join chat via WS, then fetch+render history via HTTP
  async function selectChat(chatID) {
    // Prevent reloading if already selected
    if (currentChatID === chatID) return;

    // leave old room
    if (currentChatID != null) {
      ws.send(JSON.stringify({ type: 'leave_chat', chatID: currentChatID }));
    }
    currentChatID = chatID;
    messagesEl.innerHTML = '';

    // subscribe to new room
    ws.send(JSON.stringify({ type: 'join_chat', chatID }));

    // fetch past messages
    try {
      const res = await window.api.request('/chat/messages', {
        body: JSON.stringify({
          username,
          session_token: token,
          chatID
        })
      });
      const history = Array.isArray(res.response) ? res.response : [];
      history.forEach(appendMessage);
    } catch (err) {
      console.error('history fetch error', err);
    }

    // highlight active chat
    chatListEl.querySelectorAll('li').forEach(li => {
      li.classList.toggle('active',
        Number(li.dataset.chatId) === chatID
      );
    });
  }

  // 6) Render a single message
  function appendMessage({ userID, username: msgUser, message, timestamp }) {
    // wrapper div
    const div = document.createElement('div');
    div.classList.add('message');

    // incoming vs outgoing
    if (msgUser === username) {
      div.classList.add('message-outgoing');
    } else {
      div.classList.add('message-incoming');
    }

    // format time as HH:mm
    const time = new Date(timestamp)
      .toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // header: username on left, time on right
    const header = document.createElement('div');
    header.className = 'message-header';

    const userEl = document.createElement('span');
    userEl.className = 'message-username';
    userEl.textContent = msgUser;

    const timeEl = document.createElement('span');
    timeEl.className = 'message-timestamp';
    timeEl.textContent = time;

    header.append(userEl, timeEl);

    // body
    const body = document.createElement('div');
    body.className = 'message-content';
    body.textContent = message;

    // assemble
    div.append(header, body);
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // 7) Send a new message via WS
  function sendMessage() {
    if (!currentChatID) {
      return alert('Select a chat first.');
    }
    const text = messageInput.value.trim();
    if (!text) return;
    ws.send(JSON.stringify({
      type:   'post_msg',
      chatID: currentChatID,
      text
    }));
    messageInput.value = '';
    messageInput.focus();
  }

  sendBtn.addEventListener('click', sendMessage);

  // Send message on Enter key, stay in input
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  let typingTimeout;
  messageInput.addEventListener('input', () => {
    if (!currentChatID || !ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: "typing", chatID: currentChatID }));
    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => {
      // Optional: implement stop-typing message
    }, 3000);
  });

  // 8) Create a new chat (HTTP)
  createChatBtn.addEventListener('click', async () => {
    const receiver = newChatInput.value.trim();
    if (!receiver) return;
    try {
      await window.api.request('/chat/create-chat', {
        body: JSON.stringify({ receiver, session_token: token })
      });
      newChatInput.value = '';
      await loadChats();
    } catch (err) {
      console.error('createChat error', err);
      alert('Could not create chat: ' + (err.message || err));
    }
  });

  // 9) Logout
  logoutBtn.addEventListener('click', () => {
    window.secureStore.set('refresh_token', '');
    window.secureStore.set('session_token', '');
    window.secureStore.set('username', '');
    location.href = 'login.html';
  });
});
