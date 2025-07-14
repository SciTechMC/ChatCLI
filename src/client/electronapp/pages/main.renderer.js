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
  const placeholder = document.getElementById('no-chat-selected');

  let currentChatID = null;
  let ws;
  let chatToDelete = null; // Store the chatID temporarily

  const messageControls = document.querySelector('.chat-controls');
const typingIndicator = document.getElementById('typing-indicator');

messageControls.classList.add('hidden');
document.getElementById('no-chat-selected').style.display = 'block';

  updateSendButtonState();


  function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.classList.add('toast', type);
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 500);
    }, 3000);
  }

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
      if (msg.type === "user_typing" && msg.chatID === currentChatID && msg.username.toLowerCase() !== username.toLowerCase()) {
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
      messageControls.classList.add('hidden');
      chats.forEach(({ chatID, name, online }) => {
        const li = document.createElement('li');
        li.classList.add('chat-entry');
        li.dataset.chatId = chatID;
        li.dataset.username = name;
  
        // Create the status dot
        const statusIndicator = document.createElement('div');
        statusIndicator.classList.add('status-indicator', online ? 'online' : 'offline');
  
        // Create username text
        const chatName = document.createElement('span');
        chatName.textContent = name;
        chatName.classList.add('chat-name');
  
        // Combine status dot + name
        const nameWrapper = document.createElement('div');
        nameWrapper.classList.add('chat-name-wrapper');
        nameWrapper.append(statusIndicator, chatName);
  
        // Create delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.innerHTML = '&times;';
        deleteBtn.className = 'delete-chat-btn';
        deleteBtn.title = 'Delete chat';
        deleteBtn.onclick = (e) => {
          e.stopPropagation(); // prevent triggering chat selection
          handleDeleteChat(chatID);
        };
  
        // Header row: [● name]     [×]
        const header = document.createElement('div');
        header.classList.add('chat-header');
        header.append(nameWrapper, deleteBtn);
  
        li.append(header);
        li.addEventListener('click', (e) => {
          if (e.target.closest('.delete-chat-btn')) return; // don't select chat if delete was clicked
          selectChat(chatID);
        });  
        chatListEl.appendChild(li);
      });
    } catch (err) {
      console.error('loadChats error', err);
    }
  }
  
  loadChats();
  document.getElementById('no-chat-selected').style.display = 'block';

  // Show modal for confirmation
  function showModal(message, onConfirm) {
    const modal = document.getElementById('modal-container');
    const modalMessage = document.getElementById('modal-message');
    const confirmBtn = document.getElementById('modal-confirm-btn');
    const cancelBtn = document.getElementById('modal-cancel-btn');

    modalMessage.textContent = message;
    modal.classList.remove('hidden');

    // Confirm button logic
    confirmBtn.onclick = () => {
      modal.classList.add('hidden');
      onConfirm();
    };

    // Cancel button logic
    cancelBtn.onclick = () => {
      modal.classList.add('hidden');
      chatToDelete = null; // Reset chatID
    };
  }

  // Add deleteChat function
  async function deleteChat(chatID) {
    console.log('Deleting chat with ID:', chatID); // Debugging

    try {
      await window.api.request('/chat/delete-chat', {
        body: JSON.stringify({ session_token: token, chatID })
      });
      showToast('Chat deleted successfully!', 'info');
      await loadChats(); // Reload the chat list
    } catch (err) {
      console.error('deleteChat error', err);
      showToast(`Could not delete chat: ${err.message || err}`, 'error');
    }
  }

  // Handle delete chat with confirmation
  async function handleDeleteChat(chatID) {
    chatToDelete = chatID; // Store chatID temporarily
    showModal('Are you sure you want to delete this chat?', async () => {
      if (chatToDelete) {
        await deleteChat(chatToDelete);
        chatToDelete = null; // Reset chatID after deletion
      }
    });
  }

  // 5) Join chat via WS, then fetch+render history via HTTP
  async function selectChat(chatID) {
    if (!chatID) {
      currentChatID = null;
      messagesEl.innerHTML = '';
      messageControls.classList.add('hidden');
      placeholder.style.display = 'block';
      typingIndicator.style.display = 'none';
      return;
    }
  
    placeholder.style.display = 'none';
    messageControls.classList.remove('hidden');
    typingIndicator.style.display = 'none';
  
    if (currentChatID === chatID) return;
  
    if (currentChatID != null) {
      ws.send(JSON.stringify({ type: 'leave_chat', chatID: currentChatID }));
    }
    currentChatID = chatID;
    messagesEl.innerHTML = '';
  
    ws.send(JSON.stringify({ type: 'join_chat', chatID }));
  
    try {
      const res = await window.api.request('/chat/messages', {
        body: JSON.stringify({ username, session_token: token, chatID })
      });
      const history = Array.isArray(res.response) ? res.response : [];
      history.forEach(appendMessage);
    } catch (err) {
      console.error('history fetch error', err);
    }
  
    chatListEl.querySelectorAll('li').forEach(li => {
      li.classList.toggle('active', Number(li.dataset.chatId) === chatID);
    });
  }
  
  

  // 6) Render a single message
  function appendMessage({ username: msgUser, message, timestamp }) {
    const div = document.createElement('div');
    div.classList.add('message');
  
    // Header: Username and timestamp
    const header = document.createElement('div');
    header.className = 'message-header';
  
    const userEl = document.createElement('span');
    userEl.classList.add('message-username');
    if (msgUser.toLowerCase() === username.toLowerCase()) {
      userEl.classList.add('message-username-self');
    }
    userEl.textContent = msgUser;
  
    const timeEl = document.createElement('span');
    timeEl.className = 'message-timestamp';
  
    const date = new Date(timestamp);
    const formatted = `${date.toLocaleDateString()}, ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    timeEl.textContent = formatted;
  
    header.append(userEl, timeEl);
  
    // Message text
    const body = document.createElement('div');
    body.className = 'message-content';
    body.textContent = message;
  
    div.append(header, body);
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
  

  // 7) Send a new message via WS
  function sendMessage() {
    if (!currentChatID) {
      return showToast('Select a chat first.', 'error');
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
  
    // Reset textarea height
    messageInput.style.height = 'auto';
  }

  sendBtn.addEventListener('click', sendMessage);

  // Send message on Enter key, stay in input
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = `${messageInput.scrollHeight}px`;
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
      showToast('Could not create chat: ' + (err.message || err), 'error');
    }
  });

  // 9) Logout
  logoutBtn.addEventListener('click', () => {
    window.secureStore.set('refresh_token', '');
    window.secureStore.set('session_token', '');
    window.secureStore.set('username', '');
    location.href = 'login.html';
  });
  
  function updateSendButtonState() {
    const hasContent = messageInput.value.trim().length > 0;
    sendBtn.classList.toggle('disabled', !hasContent);
  }

  messageInput.addEventListener('input', updateSendButtonState);

});