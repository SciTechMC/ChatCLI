// WebSocket configuration
const ip = "ws://127.0.0.1:8765/ws";

// =============================================
// UTILITY FUNCTIONS
// =============================================

let toastContainer;

// Modal closing functionality
function setupModalClosing() {
  // Set up close buttons for all modals
  document.querySelectorAll('.modal-close').forEach(button => {
    button.addEventListener('click', () => {
      const modal = button.closest('.modal');
      if (modal) hideModal(modal);
    });
  });

  // Set up cancel buttons for all modals
  document.querySelectorAll('.modal-button.secondary').forEach(button => {
    if (button.id.includes('cancel') || button.textContent.includes('Cancel')) {
      button.addEventListener('click', () => {
        const modal = button.closest('.modal');
        if (modal) hideModal(modal);
      });
    }
  });

  // Add Escape key support for closing modals
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const activeModal = document.querySelector('.modal.active');
      if (activeModal) hideModal(activeModal);
    }
  });
}

// Updated showModal function
function showModal(modal) {
  // Function to close the modal when clicking outside
  const closeOnBackdropClick = (event) => {
    if (event.target === modal) {
      hideModal(modal);
    }
  };

  // Remove any existing backdrop click handler
  if (modal._closeOnBackdropClick) {
    modal.removeEventListener('click', modal._closeOnBackdropClick);
  }

  // Store and add the event listener
  modal._closeOnBackdropClick = closeOnBackdropClick;
  modal.addEventListener('click', closeOnBackdropClick);

  // Show the modal
  modal.classList.add('active');
  modal.style.pointerEvents = 'all';
  modal.querySelector('.modal-content').style.transform = 'translateY(0)';
}

// Updated hideModal function
function hideModal(modal) {
  // Clean up the backdrop click handler
  if (modal._closeOnBackdropClick) {
    modal.removeEventListener('click', modal._closeOnBackdropClick);
    delete modal._closeOnBackdropClick;
  }

  // Hide the modal
  modal.classList.remove('active');
  modal.style.pointerEvents = 'none';
  modal.querySelector('.modal-content').style.transform = 'translateY(20px)';
}

// Show toast notification
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.classList.add('toast', type);
  toast.textContent = message;
  toast.style.padding = '12px 16px';
  toast.style.backgroundColor = type === 'error' ? 'var(--danger-color)' :
                              type === 'warning' ? '#f0ad4e' :
                              'var(--accent-color)';
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

// API request wrapper
async function apiRequest(endpoint, options = {}) {
  try {
    console.log(`Making request to ${endpoint} with options:`, options);
    const response = await window.api.request(endpoint, options);
    console.log(`Received response from ${endpoint}:`, response);

    if (!response || typeof response.status === 'undefined') {
      throw new Error(`Invalid response structure for ${endpoint}`);
    }

    return response;
  } catch (err) {
    console.error(`API request error for ${endpoint}:`, err);
    throw new Error(`Request failed: ${err.message}`);
  }
}

// =============================================
// MAIN APPLICATION LOGIC
// =============================================

document.addEventListener('DOMContentLoaded', async () => {
  console.log('Starting DOMContentLoaded');

  // Create toast container
  toastContainer = document.createElement('div');
  toastContainer.id = 'toast-container';
  toastContainer.style.position = 'fixed';
  toastContainer.style.top = '20px';
  toastContainer.style.right = '20px';
  toastContainer.style.zIndex = '1000';
  document.body.appendChild(toastContainer);

  // Create typing indicator
  const typingIndicator = document.createElement('div');
  typingIndicator.id = 'typing-indicator';
  typingIndicator.style.display = 'none';
  typingIndicator.style.fontSize = '12px';
  typingIndicator.style.color = 'var(--text-secondary)';
  typingIndicator.style.marginLeft = '10px';
  document.querySelector('.chat-header').appendChild(typingIndicator);

  // Set up modal closing functionality
  setupModalClosing();

  try {
    // Get stored credentials
    const token = await window.secureStore.get('session_token');
    let username = await window.secureStore.get('username');

    if (!token || !username) {
      console.log('Missing credentials, redirecting to login');
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
    const chatListEl = document.querySelector('.chat-list');
    const messagesEl = document.querySelector('.chat-messages');
    const messageInput = document.querySelector('.message-input');
    const sendBtn = document.querySelector('.send-button');
    const logoutBtn = document.querySelector('.logout-button');
    const chatTitle = document.querySelector('.chat-title');
    const editMembersBtn = document.getElementById('manageUsersBtn');

    // Create placeholder for when no chat is selected
    const placeholder = document.createElement('div');
    placeholder.id = 'no-chat-selected';
    placeholder.textContent = 'Select a chat to start messaging';
    placeholder.style.display = 'flex';
    placeholder.style.justifyContent = 'center';
    placeholder.style.alignItems = 'center';
    placeholder.style.height = '100%';
    placeholder.style.color = 'var(--text-secondary)';
    messagesEl.appendChild(placeholder);

    // Modal elements
    const profileModal = document.getElementById('profileModal');
    const profileForm = document.querySelector('#profileModal .modal-body');
    const closeProfileBtn = document.getElementById('closeProfileModal');
    const disableAccountBtn = document.querySelector('#profileModal button[name="disable"]');
    const deleteAccountBtn = document.querySelector('#profileModal button[name="delete"]');
    const createChatModal = document.getElementById('createChatModal');
    const privateChatSection = document.getElementById('privateChatSection');
    const groupChatSection = document.getElementById('groupChatSection');
    const newChatInput = document.querySelector('#privateChatSection input[name="receiver"]');
    const newGroupNameInput = document.querySelector('#groupChatSection input[name="groupName"]');
    const groupMemberInput = document.querySelector('#groupChatSection input[name="members"]');
    const createChatSubmitBtn = document.getElementById('createChatSubmitBtn');
    const closeCreateChatBtn = document.getElementById('closeCreateChat');
    const cancelCreateChatBtn = document.getElementById('cancelCreateChat');
    const groupEditorModal = document.getElementById('groupEditorModal');
    const groupMemberList = document.querySelector('#groupEditorModal .user-list');
    const editMemberInput = document.querySelector('#groupEditorModal .user-add-input');
    const editMemberAddBtn = document.querySelector('#groupEditorModal .user-add-button');
    const closeGroupEditorBtn = document.getElementById('closeGroupEditor');
    const cancelGroupEditBtn = document.getElementById('cancelGroupEdit');
    const saveGroupChangesBtn = document.getElementById('saveGroupChanges');
    const confirmationModal = document.getElementById('confirmationModal');
    const confirmationTitle = document.getElementById('confirmationTitle');
    const confirmationMessage = document.getElementById('confirmationMessage');
    const closeConfirmationModalBtn = document.getElementById('closeConfirmationModal');
    const cancelConfirmBtn = document.getElementById('cancelConfirmBtn');
    const confirmActionBtn = document.getElementById('confirmActionBtn');
    const resetPasswordModal = document.getElementById('resetPasswordModal');
    const closeResetPasswordModalBtn = document.getElementById('closeResetPasswordModal');
    const cancelResetPasswordBtn = document.getElementById('cancelResetPassword');
    const submitResetPasswordBtn = document.getElementById('submitResetPassword');

    // Application state
    let currentChatID = null;
    let ws;
    let chatToDelete = null;
    let groupMembers = [];
    let currentMembers = [];

    // Initialize create chat modal toggle state
    privateChatSection.classList.remove('hidden');
    groupChatSection.classList.add('hidden');

    // Updated confirmation modal function
    function showConfirmationModal(message, title = 'Confirm Action', onConfirm) {
      confirmationMessage.textContent = message;
      confirmationTitle.textContent = title;
      showModal(confirmationModal);

      // Clean up existing event listeners
      confirmActionBtn.onclick = null;
      cancelConfirmBtn.onclick = null;
      closeConfirmationModalBtn.onclick = null;

      // Set up new event listeners
      const confirmHandler = async () => {
        hideModal(confirmationModal);
        await onConfirm();
      };

      confirmActionBtn.onclick = confirmHandler;
      cancelConfirmBtn.onclick = () => hideModal(confirmationModal);
      closeConfirmationModalBtn.onclick = () => hideModal(confirmationModal);

      // Add keyboard support
      const keyHandler = (event) => {
        if (event.key === 'Enter') {
          event.preventDefault();
          confirmHandler();
        }
        if (event.key === 'Escape') {
          hideModal(confirmationModal);
        }
      };

      document.addEventListener('keydown', keyHandler);
      return () => document.removeEventListener('keydown', keyHandler);
    }

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
    // CORE APPLICATION FUNCTIONS
    // =============================================

    // Connect to WebSocket
    function connectWS() {
      ws = new WebSocket(ip);
      ws.addEventListener('open', () => {
        console.log('WebSocket connected');
        ws.send(JSON.stringify({ type: 'auth', token }));
      });
      ws.addEventListener('message', ({ data }) => {
        const msg = JSON.parse(data);
        if (msg.type === 'new_message' && msg.chatID === currentChatID) {
          appendMessage(msg);
        }
        if (msg.type === "user_typing" && msg.chatID === currentChatID && msg.username.toLowerCase() !== username.toLowerCase()) {
          typingIndicator.textContent = `${msg.username} is typing...`;
          typingIndicator.style.display = 'block';
          clearTimeout(typingIndicator._timeout);
          typingIndicator._timeout = setTimeout(() => {
            typingIndicator.style.display = 'none';
          }, 3000);
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
      ws.addEventListener('close', () => {
        console.log('WebSocket disconnected, reconnecting...');
        setTimeout(connectWS, 2000);
      });
      ws.addEventListener('error', (error) => {
        console.error('WebSocket error:', error);
      });
    }

    // Update send button state
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
            const res = await apiRequest('/chat/unarchive-chat', {
              body: JSON.stringify({ session_token: token, chatID })
            });
            if (!res.ok) throw new Error(res.message || 'Failed to unarchive');
            showToast('Chat unarchived!');
            archivedChatsData = archivedChatsData.filter(c => c.chatID !== chatID);
            await loadChats(); // will re-render both active and archived chats            
          } catch (err) {
            showToast(err.message || 'Could not unarchive chat', 'error');
          }
        });
    
        item.appendChild(unarchiveBtn);
        item.addEventListener('click', () => selectChat(chatID));
        chatListEl.appendChild(item);
      });
    }
    

    let archivedVisible = false;
    let archivedChatsData = [];

    // Load and render the user's chat list
    async function loadChats() {
      try {
        console.log('Loading chats...');
        const res = await apiRequest('/chat/fetch-chats', {
          body: JSON.stringify({ session_token: token })
        });
    
        if (!res.response) {
          throw new Error('No response data received');
        }
    
        const chats = Array.isArray(res.response) ? res.response : [];
        console.log('Received chats:', chats);
    
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
    
          chatInfo.appendChild(chatName);
          chatInfo.appendChild(chatPreview);
          chatItem.appendChild(chatInfo);
    
          const chatClose = document.createElement('div');
          chatClose.classList.add('chat-close');
          chatClose.innerHTML = '×';
          chatClose.title = 'Archive chat';
          chatClose.addEventListener('click', (e) => {
            e.stopPropagation();
            handleArchiveChat(chatID);
          });
    
          chatItem.appendChild(chatClose);
          chatItem.addEventListener('click', () => selectChat(chatID));
          chatListEl.appendChild(chatItem);
        });
    
        // === ARCHIVE TOGGLE INTEGRATION ===
        const archiveToggleContainer = document.createElement('div');
        archiveToggleContainer.style.textAlign = 'center';
        archiveToggleContainer.style.margin = '16px 0';
    
        const archiveToggleBtn = document.createElement('button');
        archiveToggleBtn.className = 'archived-chats-button';
        archiveToggleBtn.textContent = archivedVisible ? '📂 Hide Archived Chats' : '📁 Show Archived Chats';
    
        archiveToggleBtn.addEventListener('click', () => {
          archivedVisible = !archivedVisible;
          archiveToggleBtn.textContent = archivedVisible ? '📂 Hide Archived Chats' : '📁 Show Archived Chats';
          renderArchivedChats();
        });
    
        archiveToggleContainer.appendChild(archiveToggleBtn);
        chatListEl.appendChild(archiveToggleContainer);
    
        // Fetch archived data
        const archivedRes = await apiRequest('/chat/fetch-archived', {
          body: JSON.stringify({ session_token: token })
        });
    
        archivedChatsData = archivedRes.response || [];
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

      if (currentChatID != null && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'leave_chat', chatID: currentChatID }));
      }

      currentChatID = chatID;
      messagesEl.innerHTML = '';

      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'join_chat', chatID }));
      }

      try {
        const res = await apiRequest('/chat/messages', {
          body: JSON.stringify({ username, session_token: token, chatID })
        });

        if (res && res.response) {
          const history = Array.isArray(res.response) ? res.response : [];
          history.forEach(appendMessage);
        }
      } catch (err) {
        console.error('history fetch error:', err);
        showToast('Failed to load message history: ' + (err.message || 'Unknown error'), 'error');
      }

      document.querySelectorAll('.chat-item').forEach(el => {
        el.classList.toggle('active', el.dataset.chatId == chatID);
      });
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
    function sendMessage() {
      if (!currentChatID) {
        return showToast('Select a chat first.', 'error');
      }

      const text = messageInput.value.trim();
      if (!text) return;

      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'post_msg',
          chatID: currentChatID,
          text
        }));
      } else {
        showToast('Not connected to server. Trying to reconnect...', 'warning');
        connectWS();
        setTimeout(() => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              type: 'post_msg',
              chatID: currentChatID,
              text
            }));
          }
        }, 2000);
      }

      messageInput.value = '';
      messageInput.style.height = 'auto';
      updateSendButtonState();
    }

    // Archive a chat
    async function archiveChat(chatID) {
      try {
        const res = await apiRequest('/chat/archive-chat', {
          body: JSON.stringify({ session_token: token, chatID })
        });

        if (!res || res.status !== 'ok') {
          throw new Error('Failed to archive chat');
        }

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
    // EVENT LISTENERS
    // =============================================

    document.getElementById('viewArchivedBtn')?.addEventListener('click', async () => {
      try {
        const token = await window.secureStore.get('session_token');
        const res = await apiRequest('/chat/fetch-archived', {
          body: JSON.stringify({ session_token: token })
        });
    
        if (!res || !Array.isArray(res.response)) {
          throw new Error('Failed to fetch archived chats');
        }
    
        chatListEl.innerHTML = '';
        const title = document.createElement('div');
        title.classList.add('chat-list-title');
        title.textContent = 'Archived Chats';
        chatListEl.appendChild(title);
    
        res.response.forEach(({ chatID, name, type }) => {
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
            const res = await apiRequest('/chat/fetch-archived', {
              body: JSON.stringify({ session_token: token })
            });

            if (!res || !Array.isArray(res.response)) {
              throw new Error('Failed to fetch archived chats');
            }

            chatListEl.innerHTML = '';
            const title = document.createElement('div');
            title.classList.add('chat-list-title');
            title.textContent = 'Archived Chats';
            chatListEl.appendChild(title);

            res.response.forEach(({ chatID, name, type }) => {
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
        const res = await apiRequest('/user/profile', {
          body: JSON.stringify({ session_token: token })
        });

        if (res && res.response) {
          document.querySelector('#profileModal input[name="username"]').value = res.response.username || '';
          document.querySelector('#profileModal input[name="email"]').value = res.response.email || '';
          showModal(profileModal);
        } else {
          throw new Error('Invalid profile data received');
        }
      } catch (err) {
        showToast('Failed to load profile: ' + (err.message || 'Unknown error'), 'error');
      }
    });

    // Profile modal closing
    closeProfileBtn.addEventListener('click', () => hideModal(profileModal));
    document.getElementById('cancelProfile').addEventListener('click', () => hideModal(profileModal));

    // Submit profile updates
    if (profileForm) {
      profileForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const newUsername = document.querySelector('#profileModal input[name="username"]').value.trim();
        const newEmail = document.querySelector('#profileModal input[name="email"]').value.trim();

        try {
          const res = await apiRequest('/user/submit-profile', {
            body: JSON.stringify({
              session_token: token,
              action: 'update',
              username: newUsername,
              email: newEmail
            })
          });

          if (!res) {
            throw new Error('No response from server');
          }

          hideModal(profileModal);

          if (res.response && res.response.verificationSent) {
            showToast('Email changed - please verify your new address.', 'info');
            await window.secureStore.delete('session_token');
            await window.secureStore.delete('refresh_token');
            await window.secureStore.delete('username');
            await window.secureStore.delete('email');
            window.location.href = `verify.html?username=${encodeURIComponent(newUsername)}`;
            return;
          }

          showToast('Profile updated!', 'info');

          if (newUsername !== username) {
            await window.secureStore.set('username', newUsername);
            username = newUsername;
            if (userInfoEl) {
              userInfoEl.textContent = newUsername;
            }
          }
        } catch (err) {
          showToast('Failed to update profile: ' + (err.message || 'Unknown error'), 'error');
        }
      });
    }

    // Disable account
    if (disableAccountBtn) {
      disableAccountBtn.addEventListener('click', () => {
        hideModal(profileModal);
        showConfirmationModal(
          'Disabling your account will prevent you from logging in until you reactivate via the email we\'ll send. Continue?',
          'Disable Account',
          async () => {
            try {
              const res = await apiRequest('/user/submit-profile', {
                body: JSON.stringify({
                  session_token: token,
                  disable: 1,
                  delete: 0
                })
              });

              if (!res || res.status !== 'ok') {
                throw new Error('Failed to disable account');
              }

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
              const res = await apiRequest('/user/submit-profile', {
                body: JSON.stringify({
                  session_token: token,
                  disable: 0,
                  delete: 1
                })
              });

              if (!res || res.status !== 'ok') {
                throw new Error('Failed to delete account');
              }

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
        const token = await window.secureStore.get('session_token');
        const res = await apiRequest('/user/change-password', {
          body: JSON.stringify({
            session_token: token,
            current_password: current,
            new_password: newPw
          })
        });
      
        if (!res || res.status !== 'ok') {
          throw new Error(res?.message || 'Password update failed');
        }
      
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
      
        const token = await window.secureStore.get('session_token');
      
        if (chatType === 'private') {
          const receiver = newChatInput.value.trim();
          if (!receiver) {
            return showToast('Please enter a username', 'error');
          }
      
          try {
            const res = await apiRequest('/chat/create-chat', {
              body: JSON.stringify({
                receiver,
                session_token: token
              })
            });
      
            if (!res || res.status !== "ok") {
              throw new Error(res?.message || 'Failed to create chat');
            }
      
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
            const res = await apiRequest('/chat/create-group', {
              body: JSON.stringify({
                session_token: token,
                name: groupName,
                members: members
              })
            });
      
            if (!res || !res.response?.chatID) {
              throw new Error(res?.message || 'Failed to create group');
            }
      
            const newChatID = res.response.chatID;
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

        try {
          const res = await apiRequest('/chat/get-members', {
            body: JSON.stringify({ session_token: token, chatID: currentChatID })
          });

          if (!res || !res.response) {
            throw new Error('Failed to get group members');
          }

          currentMembers = Array.isArray(res.response) ? res.response : [];
          groupMemberList.innerHTML = '';

          currentMembers.forEach(u => {
            const userItem = document.createElement('div');
            userItem.classList.add('user-item');
            const userName = document.createElement('span');
            userName.textContent = u;
            const removeBtn = document.createElement('span');
            removeBtn.classList.add('user-remove');
            removeBtn.textContent = '×';
            removeBtn.onclick = async (e) => {
              e.stopPropagation();
              try {
                const removeRes = await apiRequest('/chat/remove-members', {
                  body: JSON.stringify({
                    session_token: token,
                    chatID: currentChatID,
                    members: [u]
                  })
                });

                if (!removeRes || !removeRes.ok) {
                  throw new Error('Failed to remove member');
                }

                userItem.remove();
                currentMembers = currentMembers.filter(member => member !== u);
              } catch (err) {
                showToast('Failed to remove member: ' + (err.message || 'Unknown error'), 'error');
              }
            };

            userItem.appendChild(userName);
            userItem.appendChild(removeBtn);
            groupMemberList.appendChild(userItem);
          });

          showModal(groupEditorModal);
        } catch (err) {
          showToast('Failed to load group members: ' + (err.message || 'Unknown error'), 'error');
        }
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
          const res = await apiRequest('/chat/add-members', {
            body: JSON.stringify({
              session_token: token,
              chatID: currentChatID,
              members: [username]
            })
          });

          if (!res || res.status !== 'ok') {
            throw new Error('Failed to add member');
          }

          const userItem = document.createElement('div');
          userItem.classList.add('user-item');
          const userName = document.createElement('span');
          userName.textContent = username;
          const removeBtn = document.createElement('span');
          removeBtn.classList.add('user-remove');
          removeBtn.textContent = '×';
          removeBtn.onclick = async (e) => {
            e.stopPropagation();
            try {
              const removeRes = await apiRequest('/chat/remove-members', {
                body: JSON.stringify({
                  session_token: token,
                  chatID: currentChatID,
                  members: [username]
                })
              });

              if (!removeRes || !removeRes.ok) {
                throw new Error('Failed to remove member');
              }

              userItem.remove();
              currentMembers = currentMembers.filter(member => member !== username);
            } catch (err) {
              showToast('Failed to remove member: ' + (err.message || 'Unknown error'), 'error');
            }
          };

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
        messageInput.style.height = 'auto';
        messageInput.style.height = `${messageInput.scrollHeight}px`;
        updateSendButtonState();

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