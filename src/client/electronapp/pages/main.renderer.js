// =============================================
// UTILITY FUNCTIONS
// =============================================
let toastContainer;
// Modal closing functionality
function setupModalClosing() {
  document.querySelectorAll('.modal-close').forEach(button => {
    button.addEventListener('click', () => {
      const modal = button.closest('.modal');
      if (modal) hideModal(modal);
    });
  });
  document.querySelectorAll('.modal-button.secondary').forEach(button => {
    if (button.id.includes('cancel') || button.textContent.includes('Cancel')) {
      button.addEventListener('click', () => {
        const modal = button.closest('.modal');
        if (modal) hideModal(modal);
      });
    }
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      const activeModal = document.querySelector('.modal.active');
      if (activeModal) hideModal(activeModal);
    }
  });
}

function showModal(modal) {
  const closeOnBackdropClick = event => {
    if (event.target === modal) hideModal(modal);
  };
  if (modal._closeOnBackdropClick) modal.removeEventListener('click', modal._closeOnBackdropClick);
  modal._closeOnBackdropClick = closeOnBackdropClick;
  modal.addEventListener('click', closeOnBackdropClick);
  modal.classList.add('active');
  modal.style.pointerEvents = 'all';
  modal.querySelector('.modal-content').style.transform = 'translateY(0)';
}

function hideModal(modal) {
  if (modal._closeOnBackdropClick) {
    modal.removeEventListener('click', modal._closeOnBackdropClick);
    delete modal._closeOnBackdropClick;
  }
  modal.classList.remove('active');
  modal.style.pointerEvents = 'none';
  modal.querySelector('.modal-content').style.transform = 'translateY(20px)';
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.classList.add('toast', type);
  toast.textContent = message;
  toast.style.padding = '12px 16px';
  toast.style.backgroundColor = type === 'error' ? 'var(--danger-color)' : type === 'warning' ? '#f0ad4e' : 'var(--accent-color)';
  toast.style.color = 'white';
  toast.style.borderRadius = '4px';
  toast.style.marginBottom = '10px';
  toast.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.2)';
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 500);
  }, 3000);
}
// =============================================
// CONFIGURATION
// =============================================
const WS_URL = 'ws://172.27.27.179:8765/ws';

// =============================================
// API REQUEST WRAPPER
// =============================================
async function apiRequest(endpoint, options = {}) {
  try {
    // window.api.request already adds BASE_URL; just forward the path as-is
    const raw = await window.api.request(endpoint, options);
    let env = raw;
    if (Array.isArray(raw)) {
      env = { status: 'ok', response: raw };
    } else if (raw && typeof raw.status === 'undefined') {
      env = raw.response !== undefined
        ? { status: 'ok', response: raw.response, message: raw.message || '' }
        : { status: 'ok', response: raw, message: '' };
    }
    if (env.status !== 'ok') throw new Error(env.message || 'Unknown error');
    return env.response;
  } catch (err) {
    throw new Error(`Request failed: ${err.message}`);
  }
}

// =============================================
// WEBSOCKET FUNCTIONS
// =============================================
let ws;
let token;
let username;
let messageInput;
let sendBtn;
let chatListEl;
let messagesEl;
let chatTitle;
let editMembersBtn;
let placeholder;
let typingIndicator;
let logoutBtn;
let profileModal;
let profileForm;
let closeProfileBtn;
let disableAccountBtn;
let deleteAccountBtn;
let createChatModal;
let privateChatSection;
let groupChatSection;
let newChatInput;
let newGroupNameInput;
let groupMemberInput;
let createChatSubmitBtn;
let closeCreateChatBtn;
let cancelCreateChatBtn;
let groupEditorModal;
let groupMemberList;
let editMemberInput;
let editMemberAddBtn;
let closeGroupEditorBtn;
let cancelGroupEditBtn;
let saveGroupChangesBtn;
let confirmationModal;
let confirmationTitle;
let confirmationMessage;
let closeConfirmationModalBtn;
let cancelConfirmBtn;
let confirmActionBtn;
let resetPasswordModal;
let closeResetPasswordModalBtn;
let cancelResetPasswordBtn;
let submitResetPasswordBtn;

const typingUsers = new Set();
const typingTimeouts = new Map();
const seenMessageIDs = new Set();

function updateTypingIndicator() {
  if (typingUsers.size === 0) {
    typingIndicator.style.display = 'none';
    return;
  }
  const users = Array.from(typingUsers);
  let text;
  if (users.length === 1) {
    text = `${users[0]} is typing...`;
  } else if (users.length === 2) {
    text = `${users[0]} and ${users[1]} are typing...`;
  } else {
    const last = users.pop();
    text = `${users.join(', ')}, and ${last} are typing...`;
  }
  typingIndicator.textContent = text;
  typingIndicator.style.display = 'block';
}

// =============================================
// CHAT MANAGEMENT FUNCTIONS
// =============================================

let currentChatID = null;
let archivedVisible = false;
let archivedChatsData = [];
let currentMembers = [];

function updateSendButtonState() {
  const hasContent = messageInput.value.trim().length > 0;
  sendBtn.classList.toggle('disabled', !hasContent);
}
function createChatItem(chatID, name, type) {
  const chatItem = document.createElement('div');
  chatItem.classList.add('chat-item');
  chatItem.dataset.chatId = chatID;
  chatItem.dataset.username = name;
  chatItem.dataset.type = type;
  const chatInfo = document.createElement('div');
  chatInfo.classList.add('chat-info');
  const chatName = document.createElement('div');
  chatName.classList.add('chat-name');
  chatName.textContent = name;
  chatInfo.appendChild(chatName);
  chatItem.appendChild(chatInfo);
  chatItem.addEventListener('click', () => selectChat(chatID));
  return chatItem;
}
function renderArchivedChats() {
  document.querySelectorAll('.chat-item.archived').forEach(el => el.remove());
  if (!archivedVisible) return;
  archivedChatsData.forEach(({ chatID, name, type }) => {
    const item = document.createElement('div');
    item.classList.add('chat-item', 'archived');
    item.dataset.chatId = chatID;
    item.dataset.username = name;
    item.dataset.type = type;
    const chatInfo = document.createElement('div');
    chatInfo.classList.add('chat-info');
    const chatName = document.createElement('div');
    chatName.classList.add('chat-name');
    chatName.textContent = name;
    chatInfo.appendChild(chatName);
    item.appendChild(chatInfo);
    // Unarchive button
    const unarchiveBtn = document.createElement('div');
    unarchiveBtn.classList.add('chat-close');
    unarchiveBtn.title = 'Unarchive';
    unarchiveBtn.innerHTML = '⤴'; // icon suggestion
    unarchiveBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      try {
        await apiRequest('/chat/unarchive-chat', {
          body: JSON.stringify({ session_token: token, chatID })
        });
        showToast('Chat unarchived successfully!', 'info');
        // ensure we switch back to the "Recent Chats" view:
        archivedVisible = false;
        // now reload the full list from scratch:
        await loadChats();
        // if the user was looking at that chat, deselect it
        if (currentChatID === chatID) selectChat(null);
      } catch (err) {
        console.error('Unarchive error:', err);
        showToast(err.message || 'Could not unarchive chat', 'error');
      }
    });
    item.appendChild(unarchiveBtn);
    item.addEventListener('click', () => selectChat(chatID));
    chatListEl.appendChild(item);
  });
}
// Load and render the user's chat list
async function loadChats() {
  try {
    const chats = await apiRequest('/chat/fetch-chats', {
      body: JSON.stringify({ session_token: token })
    });
    chatListEl.innerHTML = '';
    document.querySelector('.chat-input').classList.add('hidden');
    placeholder.style.display = 'flex';
    const title = document.createElement('div');
    title.classList.add('chat-list-title');
    title.textContent = 'Recent Chats';
    chatListEl.appendChild(title);
    if (chats.length === 0) {
      const emptyDiv = document.createElement('div');
      emptyDiv.textContent = 'No conversations yet';
      emptyDiv.style.padding = '12px 16px';
      emptyDiv.style.color = 'var(--text-secondary)';
      chatListEl.appendChild(emptyDiv);
    }
    chats.forEach(({ chatID, name, type }) => {
      const chatItem = document.createElement('div');
      chatItem.classList.add('chat-item');
      chatItem.dataset.chatId = chatID;
      chatItem.dataset.username = name;
      chatItem.dataset.type = type;
      if (type === 'private') {
        const statusIndicator = document.createElement('div');
        statusIndicator.classList.add('chat-status', 'offline');
        chatItem.appendChild(statusIndicator);
      }
      const chatInfo = document.createElement('div');
      chatInfo.classList.add('chat-info');
      const chatName = document.createElement('div');
      chatName.classList.add('chat-name');
      chatName.textContent = name;
      const chatPreview = document.createElement('div');
      chatPreview.classList.add('chat-preview');
      chatPreview.textContent = 'No messages yet';
      chatInfo.append(chatName, chatPreview);
      chatItem.append(chatInfo);
      const chatClose = document.createElement('div');
      chatClose.classList.add('chat-close');
      chatClose.innerHTML = '×';
      chatClose.title = 'Archive chat';
      chatClose.addEventListener('click', e => {
        e.stopPropagation();
        handleArchiveChat(chatID);
      });
      chatItem.append(chatClose);
      chatItem.addEventListener('click', () => selectChat(chatID));
      chatListEl.append(chatItem);
    });
    // Fetch archived data
    const archivedChats = await apiRequest('/chat/fetch-archived', {
      body: JSON.stringify({ session_token: token })
    });
    archivedChatsData = Array.isArray(archivedChats) ? archivedChats : [];
    // only show toggle if there are archived chats
    if (archivedChatsData.length > 0) {
      const archiveToggleContainer = document.createElement('div');
      archiveToggleContainer.style.textAlign = 'center';
      archiveToggleContainer.style.margin = '16px 0';
      const archiveToggleBtn = document.createElement('button');
      archiveToggleBtn.className = 'archived-chats-button';
      archiveToggleBtn.textContent = archivedVisible
        ? '📂 Hide Archived Chats'
        : '📁 Show Archived Chats';
      archiveToggleBtn.addEventListener('click', () => {
        archivedVisible = !archivedVisible;
        archiveToggleBtn.textContent = archivedVisible
          ? '📂 Hide Archived Chats'
          : '📁 Show Archived Chats';
        renderArchivedChats();
      });
      archiveToggleContainer.append(archiveToggleBtn);
      chatListEl.append(archiveToggleContainer);
    }
    renderArchivedChats();
    if (archivedVisible) renderArchivedChats();
  } catch (err) {
    console.error('loadChats error:', err);
    showToast('Failed to load chats: ' + err.message, 'error');
  }
}
// Select a chat by ID
async function selectChat(chatID) {
  if (!chatID) {
    currentChatID = null;
    messagesEl.innerHTML = '';
    const welcomeMessage = document.createElement('div');
    welcomeMessage.id = 'no-chat-selected';
    welcomeMessage.innerHTML = `
      <div style="text-align: center; padding: 20px;">
        <h2 style="margin-bottom: 10px;">Welcome to ChatCLI</h2>
        <p style="color: var(--text-secondary)">Select a chat to start messaging</p>
      </div>
    `;
    messagesEl.appendChild(welcomeMessage);
    document.querySelector('.chat-input').classList.add('hidden');
    document.querySelector('.chat-header').style.display = 'none';
    editMembersBtn.style.display = 'none';
    return;
  }
  
  // Convert chatID to number
  chatID = parseInt(chatID, 10);
  
  if (btnStartCall) btnStartCall.disabled = !chatID;
  if (btnLeave)     btnLeave.disabled     = true;
  if (btnMute)      btnMute.disabled      = true;

  const chatItem = chatListEl.querySelector(`[data-chat-id="${chatID}"]`);
  if (!chatItem) {
    console.error('Chat item not found');
    return;
  }
  const name = chatItem.dataset.username || 'Unknown Chat';
  const type = chatItem.dataset.type || 'private';
  document.querySelector('.chat-header').style.display = 'flex';
  chatTitle.textContent = name;
  if (type === 'group') {
    editMembersBtn.style.display = 'block';
  } else {
    editMembersBtn.style.display = 'none';
  }
  document.querySelector('.chat-input').classList.remove('hidden');
  typingIndicator.style.display = 'none';
  // Clear typing state when switching chats
  typingUsers.clear();
  typingTimeouts.forEach(timeout => clearTimeout(timeout));
  typingTimeouts.clear();
  if (currentChatID != null && ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'leave_chat', chatID: currentChatID }));
  }
  currentChatID = chatID;
  messagesEl.innerHTML = '';
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'join_chat', chatID }));
    // if this is a group, fetch its members
    if (document
          .querySelector(`.chat-item[data-chat-id="${chatID}"]`)
          .dataset.type === 'group') {
      loadGroupMembers(chatID);
      editMembersBtn.style.display = 'block';
    } else {
      editMembersBtn.style.display = 'none';
    }
  }
  try {
    const history = await apiRequest('/chat/messages', {
      body: JSON.stringify({ session_token: token, chatID })
    });

    // backend returns { messages:[ … ] }
    if (Array.isArray(history?.messages)) {
      history.messages.forEach(appendMessage);
    }
  } catch (err) {
    console.error('history fetch error:', err);
    showToast('Failed to load message history: ' + (err.message || 'Unknown error'), 'error');
  }
  document.querySelectorAll('.chat-item').forEach(el => {
    el.classList.toggle('active', parseInt(el.dataset.chatId, 10) === chatID);
  });
    if (currentChatID && username) {
    connectCallWS();
  }
}
// Render a single message
function appendMessage({ username: msgUser, message, timestamp }) {
  const messageDiv = document.createElement('div');
  messageDiv.classList.add('message');
  const header = document.createElement('div');
  header.className = 'message-header';
  const userEl = document.createElement('span');
  userEl.classList.add('message-sender');
  if (msgUser.toLowerCase() === username.toLowerCase()) {
    userEl.classList.add('message-sender-self');
  }
  userEl.textContent = msgUser;
  const timeEl = document.createElement('span');
  timeEl.className = 'message-time';
  const date = new Date(timestamp);
  const formatted = `${date.toLocaleDateString()}, ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  timeEl.textContent = formatted;
  header.append(userEl, timeEl);
  const body = document.createElement('div');
  body.className = 'message-text';
  body.textContent = message;
  messageDiv.append(header, body);
  messagesEl.appendChild(messageDiv);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}
// Send a new message via WebSocket
async function sendMessage() {
  if (!currentChatID) {
    return showToast('Select a chat first.', 'error');
  }
  const text = messageInput.value.trim();
  if (!text) return;
  const len = text.length;
  if (len > 2048) {
    showConfirmationModal(
      `Your message is ${len} characters long and will be split into ${Math.ceil(len / 2048)} messages. Continue?`,
      'Split Message?',
      async () => {
        const chunks = [];
        let start = 0;
        while (start < text.length) {
          let end = Math.min(text.length, start + 2048);
          if (end < text.length) {
            const lastSpace = text.lastIndexOf(' ', end);
            if (lastSpace > start) end = lastSpace;
          }
          chunks.push(text.slice(start, end));
          start = end;
        }
        for (const chunk of chunks) {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'post_msg', chatID: currentChatID, text: chunk }));
          } else {
            showToast('Not connected—reconnecting...', 'warning');
            connectWS();
            await new Promise(r => setTimeout(r, 2000));
            if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: 'post_msg', chatID: currentChatID, text: chunk }));
            }
          }
        }
        messageInput.value = '';
        messageInput.style.height = 'auto';
        updateSendButtonState();
        charCounter.style.display = 'none';
      }
    );
    return;
  }
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'post_msg', chatID: currentChatID, text }));
  } else {
    showToast('Not connected—reconnecting...', 'warning');
    connectWS();
    setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'post_msg', chatID: currentChatID, text }));
      }
    }, 2000);
  }
  messageInput.value = '';
  messageInput.style.height = 'auto';
  updateSendButtonState();
  charCounter.style.display = 'none';
}
// Archive a chat
async function archiveChat(chatID) {
  try {
    await apiRequest('/chat/archive-chat', {
      body: JSON.stringify({ session_token: token, chatID })
    });
    showToast('Chat archived successfully!', 'info');
    await loadChats();
    if (currentChatID === chatID) selectChat(null);
  } catch (err) {
    console.error('archiveChat error:', err);
    showToast(`Could not archive chat: ${err.message || 'Unknown error'}`, 'error');
  }
}
// Handle archiving a chat with confirmation
async function handleArchiveChat(chatID) {
  showConfirmationModal(
    'Are you sure you want to archive this chat? You can still rejoin it later.',
    'Archive Chat',
    async () => {
      await archiveChat(chatID);
    }
  );
}
// =============================================
// MODAL MANAGEMENT FUNCTIONS
// =============================================
// Updated confirmation modal function
function showConfirmationModal(message, title = 'Confirm Action', onConfirm) {
  confirmationMessage.textContent = message;
  confirmationTitle.textContent = title;
  showModal(confirmationModal);
  // --- set up a single keydown handler and a cleanup function ---
  const keyHandler = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      confirmHandler();
    }
    if (event.key === 'Escape') {
      cleanup();
      hideModal(confirmationModal);
    }
  };
  document.addEventListener('keydown', keyHandler);
  function cleanup() {
    document.removeEventListener('keydown', keyHandler);
    // also remove all button callbacks so nothing lingers
    confirmActionBtn.onclick = null;
    cancelConfirmBtn.onclick = null;
    closeConfirmationModalBtn.onclick = null;
  }
  // --- wire up the three “close” buttons to also run cleanup() ---
  const confirmHandler = async () => {
    cleanup();
    hideModal(confirmationModal);
    await onConfirm();
  };
  confirmActionBtn.onclick = confirmHandler;
  cancelConfirmBtn.onclick = () => {
    cleanup();
    hideModal(confirmationModal);
  };
  closeConfirmationModalBtn.onclick = () => {
    cleanup();
    hideModal(confirmationModal);
  };
  // return cleanup in case someone else needs it
  return cleanup;
}
// =============================================
// WEBSOCKET FUNCTIONS
// =============================================
let isConnecting = false;
let reconnectAttempts = 0;
const maxRetries = 5;
let iceCandidateBuffer = [];

function connectWS() {
  if (isConnecting || (ws && ws.readyState === WebSocket.OPEN)) return;

  isConnecting = true;
  ws = new WebSocket(WS_URL);

  ws.addEventListener('open', () => {
    console.log('WebSocket connected');
    reconnectAttempts = 0;
    isConnecting = false;
    ws.send(JSON.stringify({ type: 'auth', token }));
    // Send any buffered ICE candidates
    iceCandidateBuffer.forEach(obj => {
      console.log('[CALL] Sending buffered ICE candidate:', obj);
      ws.send(JSON.stringify(obj));
    });
    iceCandidateBuffer = [];
  });

  ws.addEventListener('close', () => {
    console.warn('WebSocket closed');
    isConnecting = false;
    if (reconnectAttempts < maxRetries) {
      const delay = Math.pow(2, reconnectAttempts) * 1000;
      console.log(`Reconnecting in ${delay / 1000}s...`);
      setTimeout(connectWS, delay);
      reconnectAttempts++;
    } else {
      console.error('Max retries reached, not reconnecting');
    }
  });

  ws.addEventListener('message', (event) => {
    const msg = JSON.parse(event.data);

    if (msg.type === 'auth_ack') {
      ws.send(JSON.stringify({ type: 'join_idle' }));
      return;                            // nothing else to do for this frame
    }

    // 2) a chat message broadcast from the backend
    if (msg.type === 'new_message') {
      if (seenMessageIDs.has(msg.messageID)) return;
      seenMessageIDs.add(msg.messageID);
    
      if (msg.chatID === currentChatID) {
        appendMessage({
          username:  msg.username,
          message:   msg.message,
          timestamp: msg.timestamp
        });
      } else {
        // update the preview line in the sidebar
        const preview = chatListEl
          .querySelector(`.chat-item[data-chat-id="${msg.chatID}"] .chat-preview`);
        if (preview) preview.textContent = msg.message.slice(0, 50);
      }
      return;
    }

    if (msg.type === 'error' && msg.message.includes('Invalid credentials')) {
      console.error('Fatal auth failure. Closing WebSocket.');
      ws.close(); // Prevent retry loop
    }
    if (msg.type === "user_typing" && msg.chatID === currentChatID && msg.username.toLowerCase() !== username.toLowerCase()) {
      const user = msg.username;
      // add or refresh
      typingUsers.add(user);
      clearTimeout(typingTimeouts.get(user));
      typingTimeouts.set(user, setTimeout(() => {
        typingUsers.delete(user);
        updateTypingIndicator();
      }, 3000));
      updateTypingIndicator();
    }
    if (msg.type === "user_status") {
      const chatItems = document.querySelectorAll(`.chat-item[data-username="${msg.username}"]`);
      chatItems.forEach(el => {
        const statusIndicator = el.querySelector('.chat-status');
        if (statusIndicator) {
          statusIndicator.classList.toggle("online", msg.online);
          statusIndicator.classList.toggle("offline", !msg.online);
        }
      });
    }
  });

  ws.addEventListener('error', (error) => {
    console.error('WebSocket error:', error);
    isConnecting = false;
    showToast('Connection error. Reconnecting...', 'error');
  });
}

async function loadGroupMembers(chatID) {
  try {
    const { members } = await apiRequest('/chat/get-members',
      { body: JSON.stringify({ session_token: token, chatID }) });
    // assume you have an element #groupMemberList in your modal
    const list = groupMemberList || document.querySelector('#groupEditorModal .user-list');
    list.innerHTML = '';
    members.forEach(name => {
      const el = document.createElement('div');
      el.className = 'user-item';
      el.textContent = name;
      list.appendChild(el);
    });
  } catch (err) {
    showToast('Failed loading members: ' + err.message, 'error');
  }
}
// =============================================
// MAIN APPLICATION LOGIC
// =============================================
document.addEventListener('DOMContentLoaded', async () => {
  // Create toast container
  if (btnStartCall) btnStartCall.disabled = true;
  if (btnJoinCall)  btnJoinCall.disabled  = true;
  if (btnLeave)     btnLeave.disabled     = true;
  if (btnMute)      btnMute.disabled      = true;
  toastContainer = document.createElement('div');
  toastContainer.id = 'toast-container';
  toastContainer.style.position = 'fixed';
  toastContainer.style.top = '20px';
  toastContainer.style.right = '20px';
  toastContainer.style.zIndex = '1000';
  document.body.appendChild(toastContainer);
  // Create typing indicator
  typingIndicator = document.createElement('div');
  typingIndicator.id = 'typing-indicator';
  typingIndicator.style.display = 'none';
  typingIndicator.style.fontSize = '12px';
  typingIndicator.style.color = 'var(--text-secondary)';
  const chatArea   = document.querySelector('.chat-area');
  const chatInput  = document.querySelector('.chat-input');
  chatArea.insertBefore(typingIndicator, chatInput);
  // Set up modal closing functionality
  setupModalClosing();
  try {
    // Get stored credentials
    token = await window.secureStore.get('session_token');
    username = await window.secureStore.get('username');
    if (!token || !username) {
      window.location.href = 'login.html';
      return;
    }
    // Set up username display
    const userInfoEl = document.querySelector('.username');
    if (userInfoEl) {
      userInfoEl.textContent = username;
      userInfoEl.style.wordBreak = 'break-all';
      userInfoEl.style.fontWeight = '500';
      userInfoEl.style.fontSize = '14px';
      userInfoEl.style.maxWidth = '100%';
      userInfoEl.style.overflowWrap = 'break-word';
      userInfoEl.style.color = 'var(--text-primary)';
    }
    // Cache DOM elements
    chatListEl = document.querySelector('.chat-list');
    messagesEl = document.querySelector('.chat-messages');
    messageInput = document.querySelector('.message-input');
    charCounter   = document.getElementById('charCounter');
    sendBtn = document.querySelector('.send-button');
    logoutBtn = document.querySelector('.logout-button');
    chatTitle = document.querySelector('.chat-title');
    editMembersBtn = document.getElementById('manageUsersBtn');
    // Create placeholder for when no chat is selected
    placeholder = document.createElement('div');
    placeholder.id = 'no-chat-selected';
    placeholder.textContent = 'Select a chat to start messaging';
    placeholder.style.display = 'flex';
    placeholder.style.justifyContent = 'center';
    placeholder.style.alignItems = 'center';
    placeholder.style.height = '100%';
    placeholder.style.color = 'var(--text-secondary)';
    messagesEl.appendChild(placeholder);
    // Modal elements
    profileModal = document.getElementById('profileModal');
    profileForm = document.getElementById('profileForm');
    closeProfileBtn = document.getElementById('closeProfileModal');
    cancelProfileBtn = document.getElementById('cancelProfile');
    disableAccountBtn = document.querySelector('#profileModal button[name="disable"]');
    deleteAccountBtn = document.querySelector('#profileModal button[name="delete"]');
    createChatModal = document.getElementById('createChatModal');
    privateChatSection = document.getElementById('privateChatSection');
    groupChatSection = document.getElementById('groupChatSection');
    newChatInput = document.querySelector('#privateChatSection input[name="receiver"]');
    newGroupNameInput = document.querySelector('#groupChatSection input[name="groupName"]');
    groupMemberInput = document.querySelector('#groupChatSection input[name="members"]');
    createChatSubmitBtn = document.getElementById('createChatSubmitBtn');
    closeCreateChatBtn = document.getElementById('closeCreateChat');
    cancelCreateChatBtn = document.getElementById('cancelCreateChat');
    groupEditorModal = document.getElementById('groupEditorModal');
    groupMemberList = document.querySelector('#groupEditorModal .user-list');
    editMemberInput = document.querySelector('#groupEditorModal .user-add-input');
    editMemberAddBtn = document.querySelector('#groupEditorModal .user-add-button');
    closeGroupEditorBtn = document.getElementById('closeGroupEditor');
    cancelGroupEditBtn = document.getElementById('cancelGroupEdit');
    saveGroupChangesBtn = document.getElementById('saveGroupChanges');
    confirmationModal = document.getElementById('confirmationModal');
    confirmationTitle = document.getElementById('confirmationTitle');
    confirmationMessage = document.getElementById('confirmationMessage');
    closeConfirmationModalBtn = document.getElementById('closeConfirmationModal');
    cancelConfirmBtn = document.getElementById('cancelConfirmBtn');
    confirmActionBtn = document.getElementById('confirmActionBtn');
    resetPasswordModal = document.getElementById('resetPasswordModal');
    closeResetPasswordModalBtn = document.getElementById('closeResetPasswordModal');
    cancelResetPasswordBtn = document.getElementById('cancelResetPassword');
    submitResetPasswordBtn = document.getElementById('submitResetPassword');
    // Initialize create chat modal toggle state
    privateChatSection.classList.remove('hidden');
    groupChatSection.classList.add('hidden');
    closeProfileBtn.addEventListener('click',  () => hideModal(profileModal));
    cancelProfileBtn.addEventListener('click', () => hideModal(profileModal));
    profileForm.addEventListener('submit', async e => {
      e.preventDefault();
      const newUsername = profileForm.querySelector('input[name="username"]').value.trim();
      const newEmail    = profileForm.querySelector('input[name="email"]').value.trim();
      try {
        const result = await apiRequest('/user/submit-profile', {
          body: JSON.stringify({
            session_token: token,
            username: newUsername,
            email: newEmail
          })
        });
        hideModal(profileModal);
        if (result.verificationSent) {
          showToast('Email changed—please verify.', 'info');
          window.location.href = `verify.html?username=${encodeURIComponent(newUsername)}`;
        } else {
          showToast('Profile updated!', 'info');
          document.querySelector('.username').textContent = result.username || newUsername;
        }
      } catch (err) {
        showToast('Failed to update profile: ' + err.message, 'error');
      }
    });
    // Set up radio button event listeners for create chat modal
    document.querySelectorAll('input[name="chatType"]').forEach(radio => {
      radio.addEventListener('change', function() {
        if (this.value === 'private') {
          privateChatSection.classList.remove('hidden');
          groupChatSection.classList.add('hidden');
          // Clear group inputs when switching to private
          if (newGroupNameInput) newGroupNameInput.value = '';
          if (groupMemberInput) groupMemberInput.value = '';
        } else {
          privateChatSection.classList.add('hidden');
          groupChatSection.classList.remove('hidden');
          // Clear private input when switching to group
          if (newChatInput) newChatInput.value = '';
        }
      });
    });
    // Create chat modal opening handler
    document.getElementById('openCreateChat').addEventListener('click', () => {
      const selectedType = document.querySelector('input[name="chatType"]:checked')?.value;
      if (selectedType === 'group') {
        privateChatSection.classList.add('hidden');
        groupChatSection.classList.remove('hidden');
      } else {
        privateChatSection.classList.remove('hidden');
        groupChatSection.classList.add('hidden');
      }
      newChatInput.value = '';
      newGroupNameInput.value = '';
      groupMemberInput.value = '';
      showModal(createChatModal);
    });
    // =============================================
    // EVENT LISTENERS
    // =============================================
    document.getElementById('viewArchivedBtn')?.addEventListener('click', async () => {
      try {
        const archivedChats = await apiRequest('/chat/fetch-archived', {
          body: JSON.stringify({ session_token: token })
        });
        if (!Array.isArray(archivedChats)) {
          throw new Error('Failed to fetch archived chats');
        }
        chatListEl.innerHTML = '';
        const title = document.createElement('div');
        title.classList.add('chat-list-title');
        title.textContent = 'Archived Chats';
        chatListEl.appendChild(title);
        archivedChats.forEach(({ chatID, name, type }) => {
          const chatItem = document.createElement('div');
          chatItem.classList.add('chat-item');
          chatItem.dataset.chatId = chatID;
          chatItem.dataset.username = name;
          chatItem.dataset.type = type;
          const chatInfo = document.createElement('div');
          chatInfo.classList.add('chat-info');
          const chatName = document.createElement('div');
          chatName.classList.add('chat-name');
          chatName.textContent = name;
          chatInfo.appendChild(chatName);
          chatItem.appendChild(chatInfo);
          chatItem.addEventListener('click', () => selectChat(chatID));
          chatListEl.appendChild(chatItem);
          // Add Archived Chats button at the bottom
          const archivedBtnContainer = document.createElement('div');
          archivedBtnContainer.classList.add('chat-archived-entry');
          const archivedBtn = document.createElement('button');
          archivedBtn.classList.add('archived-chats-button');
          archivedBtn.id = 'viewArchivedBtn';
          archivedBtn.innerText = '📁 View Archived Chats';
          archivedBtn.addEventListener('click', async () => {
            try {
              const archivedChats = await apiRequest('/chat/fetch-archived', {
                body: JSON.stringify({ session_token: token })
              });
              if (!Array.isArray(archivedChats)) {
                throw new Error('Failed to fetch archived chats');
              }
              chatListEl.innerHTML = '';
              const title = document.createElement('div');
              title.classList.add('chat-list-title');
              title.textContent = 'Archived Chats';
              chatListEl.appendChild(title);
              archivedChats.forEach(({ chatID, name, type }) => {
                const chatItem = document.createElement('div');
                chatItem.classList.add('chat-item');
                chatItem.dataset.chatId = chatID;
                chatItem.dataset.username = name;
                chatItem.dataset.type = type;
                const chatInfo = document.createElement('div');
                chatInfo.classList.add('chat-info');
                const chatName = document.createElement('div');
                chatName.classList.add('chat-name');
                chatName.textContent = name;
                chatInfo.appendChild(chatName);
                chatItem.appendChild(chatInfo);
                chatItem.addEventListener('click', () => selectChat(chatID));
                chatListEl.appendChild(chatItem);
              });
              showToast('Showing archived chats', 'info');
            } catch (err) {
              showToast(err.message || 'Could not load archived chats', 'error');
            }
          });
          archivedBtnContainer.appendChild(archivedBtn);
          chatListEl.appendChild(archivedBtnContainer);
        });
        showToast('Showing archived chats', 'info');
      } catch (err) {
        showToast(err.message || 'Could not load archived chats', 'error');
      }
    });
    // Profile modal logic
    document.getElementById('profileBtn').addEventListener('click', async () => {
      try {
        const profile = await apiRequest('/user/profile', {
          body: JSON.stringify({ session_token: token })
        });
        document.querySelector('#profileModal input[name="username"]').value = profile.username || '';
        document.querySelector('#profileModal input[name="email"]').value = profile.email || '';
        showModal(profileModal);
      } catch (err) {
        showToast('Failed to load profile: ' + (err.message || 'Unknown error'), 'error');
      }
    });
    // Profile modal closing
    closeProfileBtn.addEventListener('click', () => hideModal(profileModal));
    document.getElementById('cancelProfile').addEventListener('click', () => hideModal(profileModal));
    // Disable account
    if (disableAccountBtn) {
      disableAccountBtn.addEventListener('click', () => {
        hideModal(profileModal);
        showConfirmationModal(
          'Disabling your account will prevent you from logging in until you reactivate via the email we\'ll send. Continue?',
          'Disable Account',
          async () => {
            try {
              await apiRequest('/user/submit-profile', {
                body: JSON.stringify({
                  session_token: token,
                  disable: 1,
                  delete: 0
                })
              });
              showToast('Account disabled.', 'warning');
              await window.secureStore.delete('session_token');
              await window.secureStore.delete('refresh_token');
              await window.secureStore.delete('username');
              await window.secureStore.delete('email');
              window.location.href = 'index.html';
            } catch (err) {
              showToast('Failed to disable account: ' + (err.message || 'Unknown error'), 'error');
            }
          }
        );
      });
    }
    // Delete account
    if (deleteAccountBtn) {
      deleteAccountBtn.addEventListener('click', () => {
        hideModal(profileModal);
        showConfirmationModal(
          'Warning: This will PERMANENTLY DELETE your account and all associated data, including messages and chats. This action cannot be undone. Continue?',
          'Delete Account',
          async () => {
            try {
              await apiRequest('/user/submit-profile', {
                body: JSON.stringify({
                  session_token: token,
                  disable: 0,
                  delete: 1
                })
              });
              showToast('Account deleted.', 'error');
              await window.secureStore.delete('session_token');
              await window.secureStore.delete('refresh_token');
              await window.secureStore.delete('username');
              await window.secureStore.delete('email');
              window.location.href = 'index.html';
            } catch (err) {
              showToast('Failed to delete account: ' + (err.message || 'Unknown error'), 'error');
            }
          }
        );
      });
    }
    document.getElementById('changePasswordBtn')?.addEventListener('click', () => {
      document.querySelector('#resetPasswordModal input[name="currentPassword"]').value = '';
      document.querySelector('#resetPasswordModal input[name="newPassword"]').value = '';
      document.querySelector('#resetPasswordModal input[name="confirmPassword"]').value = '';
      showModal(resetPasswordModal);
    });
    closeResetPasswordModalBtn.addEventListener('click', () => hideModal(resetPasswordModal));
    cancelResetPasswordBtn.addEventListener('click', () => hideModal(resetPasswordModal));
    submitResetPasswordBtn.addEventListener('click', async () => {
      const current = document.querySelector('#resetPasswordModal input[name="currentPassword"]').value.trim();
      const newPw = document.querySelector('#resetPasswordModal input[name="newPassword"]').value.trim();
      const confirmPw = document.querySelector('#resetPasswordModal input[name="confirmPassword"]').value.trim();
      // Basic client-side validation
      if (!current || !newPw || !confirmPw) {
        return showToast('All fields are required', 'error');
      }
      if (newPw !== confirmPw) {
        return showToast('New passwords do not match', 'error');
      }
      if (newPw.length < 8 || !/\d/.test(newPw) || !/[a-zA-Z]/.test(newPw)) {
        return showToast('Password must be at least 8 characters and include letters and numbers', 'error');
      }
      try {
        await apiRequest('/user/change-password', {
          body: JSON.stringify({
            session_token: token,
            current_password: current,
            new_password: newPw
          })
        });
        showToast('Password updated. Please log in again.', 'info');
        hideModal(resetPasswordModal);
        // Strip all PII
        await window.secureStore.delete('session_token');
        await window.secureStore.delete('refresh_token');
        await window.secureStore.delete('username');
        await window.secureStore.delete('email');
        // Redirect to login
        setTimeout(() => {
          window.location.href = 'login.html';
        }, 1000);
      } catch (err) {
        showToast(err.message || 'Password change failed', 'error');
      }
    });
    // Create chat modal closing
    if (closeCreateChatBtn) {
      closeCreateChatBtn.addEventListener('click', () => hideModal(createChatModal));
    }
    if (cancelCreateChatBtn) {
      cancelCreateChatBtn.addEventListener('click', () => hideModal(createChatModal));
    }
    // Create chat (private or group)
    if (createChatSubmitBtn) {
      createChatSubmitBtn.addEventListener('click', async () => {
        const chatType = document.querySelector('input[name="chatType"]:checked')?.value;
        if (!chatType) {
          return showToast('Please select a chat type', 'error');
        }
        if (chatType === 'private') {
          const receiver = newChatInput.value.trim();
          if (!receiver) {
            return showToast('Please enter a username', 'error');
          }
          try {
            await apiRequest('/chat/create-chat', {
              body: JSON.stringify({
                receiver,
                session_token: token
              })
            });
            showToast('Private chat created!', 'info');
            hideModal(createChatModal);
            newChatInput.value = '';
            await loadChats();
          } catch (err) {
            showToast(err.message || 'Could not create private chat', 'error');
          }
        } else if (chatType === 'group') {
          const groupName = newGroupNameInput.value.trim();
          const membersInput = groupMemberInput.value.trim();
          if (!groupName) return showToast('Please enter a group name', 'error');
          if (!membersInput) return showToast('Please add at least one member', 'error');
          const members = membersInput.split(',')
            .map(m => m.trim())
            .filter(Boolean);
          try {
            const result = await apiRequest('/chat/create-group', {
              body: JSON.stringify({
                session_token: token,
                name: groupName,
                members: members
              })
            });
            if (!result.chatID) {
              throw new Error('Failed to create group');
            }
            const newChatID = result.chatID;
            showToast('Group created!', 'info');
            hideModal(createChatModal);
            newGroupNameInput.value = '';
            groupMemberInput.value = '';
            await loadChats();
            selectChat(newChatID);
          } catch (err) {
            showToast(err.message || 'Could not create group', 'error');
          }
        }
      });
    }
    // Group editor modal logic
    if (editMembersBtn) {
      editMembersBtn.addEventListener('click', async () => {
        if (!currentChatID) return;
        // 1) Fetch current members
        let members;
        try {
          const res = await apiRequest('/chat/get-members', {
            body: JSON.stringify({ session_token: token, chatID: currentChatID })
          });
          members = res.members;
        } catch (err) {
          return showToast('Failed to load group members: ' + err.message, 'error');
        }
        if (!Array.isArray(members)) {
          return showToast('Failed to load group members', 'error');
        }
        currentMembers = members;
        // 2) Render each member with the new click logic
        groupMemberList.innerHTML = '';
        const me = username.toLowerCase();
        currentMembers.forEach(member => {
          const userItem = document.createElement('div');
          userItem.classList.add('user-item');
          const userName = document.createElement('span');
          userName.textContent = member;
          const removeBtn = document.createElement('span');
          removeBtn.classList.add('user-remove');
          removeBtn.textContent = '×';
          removeBtn.addEventListener('click', e => {
            e.stopPropagation();
            // actual API call & UI removal
            const performRemoval = async () => {
              try {
                await apiRequest('/chat/remove-members', {
                  body: JSON.stringify({
                    session_token: token,
                    chatID: currentChatID,
                    members: [member]
                  })
                });
                userItem.remove();
                currentMembers = currentMembers.filter(u => u !== member);
              } catch (err) {
                showToast('Failed to remove member: ' + err.message, 'error');
              }
            };
            // If I'm removing *myself*, confirm first
            if (member.toLowerCase() === me) {
              showConfirmationModal(
                'Are you sure you want to leave this group? This cannot be undone unless someone else adds you back.',
                'Leave Group',
                async () => {
                  await performRemoval();
                  // refresh sidebar & clear chat
                  await loadChats();
                  selectChat(null);
                  hideModal(groupEditorModal);
                }
              );
            } else {
              // removing someone else
              performRemoval();
            }
          });
          userItem.append(userName, removeBtn);
          groupMemberList.appendChild(userItem);
        });
        showModal(groupEditorModal);
      });
    }
    if (closeGroupEditorBtn) {
      closeGroupEditorBtn.addEventListener('click', () => hideModal(groupEditorModal));
    }
    if (cancelGroupEditBtn) {
      cancelGroupEditBtn.addEventListener('click', () => hideModal(groupEditorModal));
    }
    // Add member to group
    if (editMemberAddBtn) {
      editMemberAddBtn.addEventListener('click', async () => {
        const username = editMemberInput.value.trim();
        if (!username) return;
        if (currentMembers.includes(username)) {
          return showToast(`${username} is already in the group`, 'warning');
        }
        try {
          await apiRequest('/chat/add-members', {
            body: JSON.stringify({
              session_token: token,
              chatID: currentChatID,
              members: [username]
            })
          });
          const userItem = document.createElement('div');
          userItem.classList.add('user-item');
          const userName = document.createElement('span');
          userName.textContent = username;
          const removeBtn = document.createElement('span');
          removeBtn.classList.add('user-remove');
          removeBtn.textContent = '×';
          removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            // 1) wrap the actual delete logic in its own function
            const doRemove = async () => {
              try {
                await apiRequest('/chat/remove-members', {
                  body: JSON.stringify({
                    session_token: token,
                    chatID: currentChatID,
                    members: [username]
                  })
                });
                // remove from UI
                userItem.remove();
                currentMembers = currentMembers.filter(u => u !== username);
              } catch (err) {
                showToast('Failed to remove member: ' + err.message, 'error');
              }
            };
            // 2) if they're removing *themselves*, show confirmation first
            if (username.toLowerCase() === me.toLowerCase()) {
              showConfirmationModal(
                'Are you sure you want to leave this group? This cannot be undone unless someone else adds you back.',
                'Leave Group',
                async () => {
                  await doRemove();
                  // 3) once they leave, refresh sidebar and clear chat pane:
                  await loadChats();
                  selectChat(null);
                }
              );
            } else {
              // removing someone else – no confirm
              doRemove();
            }
          });
          userItem.appendChild(userName);
          userItem.appendChild(removeBtn);
          groupMemberList.appendChild(userItem);
          currentMembers.push(username);
          editMemberInput.value = '';
        } catch (err) {
          showToast('Failed to add member: ' + (err.message || 'Unknown error'), 'error');
        }
      });
    }
    // Save group changes
    if (saveGroupChangesBtn) {
      saveGroupChangesBtn.addEventListener('click', () => {
        hideModal(groupEditorModal);
      });
    }
    // Logout
    if (logoutBtn) {
      logoutBtn.addEventListener('click', async () => {
        try {
          await window.secureStore.delete('session_token');
          await window.secureStore.delete('refresh_token');
          await window.secureStore.delete('username');
          await window.secureStore.delete('email');
          window.location.href = 'login.html';
        } catch (err) {
          console.error('Logout error:', err);
          showToast('Failed to logout: ' + (err.message || 'Unknown error'), 'error');
        }
      });
    }
    // Event listeners for message input
    if (sendBtn) {
      sendBtn.addEventListener('click', sendMessage);
    }
    if (messageInput) {
      messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendMessage();
        }
      });
      messageInput.addEventListener('input', () => {
        // auto‐resize up to max‐height, then scroll
        messageInput.style.height = 'auto';
        const maxH = 200;
        const needed = messageInput.scrollHeight;
        if (needed <= maxH) {
          messageInput.style.height = `${needed}px`;
          messageInput.style.overflowY = 'hidden';
        } else {
          messageInput.style.height = `${maxH}px`;
          messageInput.style.overflowY = 'auto';
        }
        updateSendButtonState();
        // live char counter
        const len = messageInput.value.length;
        if (len >= 1950) {
          charCounter.style.display = 'block';
          charCounter.textContent = len <= 2100
            ? `${len}/2048`
            : 'Message too long';
        } else {
          charCounter.style.display = 'none';
        }
        // highlight over‐limit
        messageInput.classList.toggle('error', len > 2048);
        charCounter.classList.toggle('error', len > 2048);
        if (!currentChatID || !ws || ws.readyState !== WebSocket.OPEN) return;
        ws.send(JSON.stringify({ type: "typing", chatID: currentChatID }));
      });
    }
    // Initialize the application
    connectWS();
    await loadChats();
    updateSendButtonState();
  } catch (err) {
    console.error('Initialization error:', err);
    showToast('Failed to initialize application: ' + (err.message || 'Unknown error'), 'error');
    setTimeout(() => {
      window.location.href = 'login.html';
    }, 2000);
  }
});

// =============================================
// Call Functions
// =============================================

// --- config ---
const iceServers = [{ urls: "stun:stun.l.google.com:19302" }];

// --- dom ---
const statusEl     = document.getElementById('status');
const btnStartCall = document.getElementById('btnStartCall');
const btnJoinCall  = document.getElementById('btnJoinCall');
const btnLeave     = document.getElementById('btnLeave');
const btnMute      = document.getElementById('btnMute');
const remoteAudio  = document.getElementById('remoteAudio');
const setStatus = (t, cls='') => { 
  if (statusEl) { 
    statusEl.textContent = t; 
    statusEl.className = 'status '+cls; 
  }
  console.log(`[CALL] Status: ${t} (${cls})`);
};

// --- state ---
let callWS, pc, localStream;
let inCall = false;
let joiningArmed = false;
let pendingOffer = null;
let isMuted = false;

// --- media ---
async function getMic() {
  console.log('[CALL] getMic called');
  if (localStream) {
    console.log('[CALL] Returning cached localStream');
    return localStream;
  }
  try {
    localStream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      video: false
    });
    console.log('[CALL] Got localStream:', localStream);
    localStream.getAudioTracks().forEach(t => t.enabled = !isMuted);
    return localStream;
  } catch (err) {
    console.error('[CALL] getMic error:', err);
    setStatus('Microphone error', 'warn');
    throw err;
  }
}

// --- peer connection ---
function createPC() {
  console.log('[CALL] createPC called');
  pc = new RTCPeerConnection({ iceServers });
  localStream.getAudioTracks().forEach(track => {
    pc.addTrack(track, localStream);
    console.log('[CALL] Added local audio track:', track);
  });
  pc.ontrack = (e) => { 
    console.log('[CALL] ontrack event:', e);
    remoteAudio.srcObject = e.streams[0]; 
  };
  pc.onicecandidate = (e) => { 
    console.log('[CALL] ICE candidate:', e.candidate);
    if (e.candidate) callSend({ type: 'ice-candidate', chatID: currentChatID, candidate: e.candidate }); 
  };
  pc.onconnectionstatechange = () => {
    console.log('[CALL] pc connectionState:', pc.connectionState);
    if (pc.connectionState === 'connected') setStatus('Connected ✅','ok');
    if (['failed','disconnected','closed'].includes(pc.connectionState)) setStatus('Call ended / issue','warn');
  };
}

// --- signaling ---
function connectCallWS() {
  if (!currentChatID || !username) {
    console.warn('[CALL] connectCallWS: Missing currentChatID or username');
    return;
  }
  const callUrl = WS_URL.replace(/\/ws$/, `/ws/${currentChatID}/${username}`);
  console.log('[CALL] Connecting to signaling WS:', callUrl);
  callWS = new WebSocket(callUrl);
  callWS.onopen    = () => { 
    console.log('[CALL] Call WS connected');
    setStatus('Call WS connected ✅');
    // Send any buffered ICE candidates
    iceCandidateBuffer.forEach(obj => {
      console.log('[CALL] Sending buffered ICE candidate:', obj);
      callWS.send(JSON.stringify(obj));
    });
    iceCandidateBuffer = [];
  };
  callWS.onclose   = () => { 
    console.log('[CALL] Call WS closed');
    setStatus('Call WS closed ❌','warn');
  };
  callWS.onmessage = async (ev) => {
    const msg = JSON.parse(ev.data);
    console.log('[CALL] WS message:', msg);
    if (msg.type === 'call-started' && !inCall) {
      btnJoinCall.disabled = false;
      setStatus(`${msg.from} started a call — click Join`, 'ok');
    }
    if (msg.type === 'offer') {
      console.log('[CALL] Received offer:', msg.sdp);
      if (!joiningArmed) { 
        pendingOffer = msg.sdp; 
        btnJoinCall.disabled = false; 
        setStatus('Incoming call — click Join','ok'); 
        return; 
      }
      if (!pc) { 
        await getMic(); 
        createPC(); 
      }
      await pc.setRemoteDescription(new RTCSessionDescription(msg.sdp));
      console.log('[CALL] Set remote description (offer)');
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      console.log('[CALL] Created and set local answer');
      callSend({ type: 'answer', chatID: currentChatID, sdp: answer });
      inCall = true; btnLeave.disabled = false; btnMute.disabled = false;
    }
    if (msg.type === 'answer' && pc && pc.signalingState === 'have-local-offer') {
      console.log('[CALL] Received answer:', msg.sdp);
      await pc.setRemoteDescription(new RTCSessionDescription(msg.sdp));
      btnMute.disabled = false;
    }
    if (msg.type === 'ice-candidate' && pc && msg.candidate) {
      console.log('[CALL] Received ICE candidate:', msg.candidate);
      try { await pc.addIceCandidate(new RTCIceCandidate(msg.candidate)); } catch (e) { 
        console.error('[CALL] ICE add error', e); 
      }
    }
    if (msg.type === 'leave') {
      console.log('[CALL] Peer left');
      endCall('Peer left');
    }
  };
}
function callSend(obj) { 
  if (callWS && callWS.readyState === WebSocket.OPEN) {
    console.log('[CALL] Sending signaling message:', obj);
    callWS.send(JSON.stringify(obj)); 
  } else {
    console.warn('[CALL] callSend: WebSocket not open', obj);
    // Buffer ICE candidates until WS is open
    if (obj.type === 'ice-candidate') {
      iceCandidateBuffer.push(obj);
      console.log('[CALL] ICE candidate buffered');
    }
  }
}


// --- flows ---
async function startCall() {
  console.log('[CALL] startCall called');
  callSend({ type: 'call-started', chatID: currentChatID });
  await getMic(); 
  createPC();
  const offer = await pc.createOffer({ offerToReceiveAudio: true });
  await pc.setLocalDescription(offer);
  console.log('[CALL] Created and set local offer:', offer);
  callSend({ type: 'offer', chatID: currentChatID, sdp: offer });
  inCall = true;
  btnJoinCall.disabled = true;
  btnLeave.disabled = false;
  btnMute.disabled = false;
  setStatus('Calling…');
}

async function joinCall() {
  console.log('[CALL] joinCall called');
  joiningArmed = true;
  await getMic(); 
  createPC();
  if (pendingOffer) {
    console.log('[CALL] Using pending offer');
    await pc.setRemoteDescription(new RTCSessionDescription(pendingOffer));
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    console.log('[CALL] Created and set local answer:', answer);
    callSend({ type: 'answer', chatID: currentChatID, sdp: answer });
    pendingOffer = null;
    inCall = true; btnLeave.disabled = false; btnMute.disabled = false; setStatus('Joining…');
  } else {
    setStatus('Joining… (waiting for offer)');
    console.log('[CALL] No pending offer, waiting...');
  }
  btnJoinCall.disabled = true;
}

function endCall(reason = 'Ended') {
  console.log('[CALL] endCall called:', reason);
  if (pc) { try { pc.close(); } catch (e) { console.error('[CALL] Error closing pc:', e); } pc = null; }
  if (localStream) { localStream.getTracks().forEach(t => t.stop()); localStream = null; }
  if (inCall) callSend({ type: 'leave', chatID: currentChatID, reason });
  inCall = false; joiningArmed = false; pendingOffer = null; isMuted = false;
  btnLeave.disabled = true; btnJoinCall.disabled = true; btnMute.disabled = true;
  setStatus(reason);
}

// --- mute ---
function toggleMute() {
  console.log('[CALL] toggleMute called');
  if (!localStream) {
    console.warn('[CALL] toggleMute: No localStream');
    return;
  }
  isMuted = !isMuted;
  localStream.getAudioTracks().forEach(t => t.enabled = !isMuted);
  btnMute.textContent = isMuted ? 'Unmute' : 'Mute';
  setStatus(isMuted ? 'Muted' : 'Unmuted');
}

// --- wire UI + connect WS ---
if (btnStartCall) btnStartCall.onclick = startCall;
if (btnJoinCall)  btnJoinCall.onclick  = joinCall;
if (btnLeave)     btnLeave.onclick     = () => endCall('You left');
if (btnMute)      btnMute.onclick      = toggleMute;
document.addEventListener('DOMContentLoaded', () => {
  console.log('[CALL] DOMContentLoaded: connecting call WS');
});