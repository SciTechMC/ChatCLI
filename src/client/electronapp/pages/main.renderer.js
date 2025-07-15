// main.renderer.js

const ip = "ws://127.0.0.1:8765/ws";

document.addEventListener('DOMContentLoaded', async () => {
  // 1) Get stored credentials
  const token    = await window.secureStore.get('session_token');
  let username = await window.secureStore.get('username');
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

  // —— PROFILE MODAL LOGIC (unified endpoints) —— 
const profileModal      = document.getElementById('profile-modal');
const profileForm       = document.getElementById('profile-form');
const closeProfileBtn   = document.getElementById('close-profile-modal');
const disableAccountBtn = document.getElementById('disable-account-btn');
const deleteAccountBtn  = document.getElementById('delete-account-btn');

// 1) Open & fetch current data from /user/profile
userInfoEl.style.cursor = 'pointer';
userInfoEl.addEventListener('click', async () => {
  profileModal.classList.remove('hidden');
  try {
    // call your Node/IPC wrapper — it throws on non-OK statuses
    const res = await window.api.request('/user/profile', {
      body: JSON.stringify({ session_token: token })
    });
    // unwrap the real data
    const { username: u, email: e } = res.response;
    document.getElementById('username').value = u;
    document.getElementById('email').value    = e;
  } catch (err) {
    showToast(err.message, 'error');
  }
});

// 2) Close modal
closeProfileBtn.addEventListener('click', () => {
  profileModal.classList.add('hidden');
});

// 3) Submit updates (and disable/delete) all to /user/submit-profile
async function submitAction(payload) {
  // again, your wrapper will throw on error and return { response, message, ... }
  const res = await window.api.request('/user/submit-profile', {
    body: JSON.stringify(payload)
  });
  return res;  // you can inspect res.response or res.message if needed
}

// —— PROFILE MODAL LOGIC (flags payload) —— 
async function submitProfile(payload) {
  // Always send session_token + whatever flags/fields you need
  const token = await window.secureStore.get('session_token');
  return window.api.request('/user/submit-profile', {
    body: JSON.stringify({ session_token: token, ...payload })
  });
}

  // — Save changes (with email‐change logout & redirect) —
  profileForm.addEventListener('submit', async e => {
    e.preventDefault();
    const newU = document.getElementById('username').value.trim();
    const newE = document.getElementById('email').value.trim();

    try {
      // send update, backend will set `verificationSent: true` if email changed
      const res = await submitProfile({ action: 'update', username: newU, email: newE });

      // always hide the modal
      profileModal.classList.add('hidden');

      // —––– EMAIL CHANGED: FORCE LOGOUT & REDIRECT –––—
      if (res.response.verificationSent) {
        showToast('Email changed – please verify your new address.', 'info');

        // 1) clear both tokens
        await window.secureStore.delete('session_token');
        await window.secureStore.delete('refresh_token');
        // 2) clear all stored user info
        await window.secureStore.delete('username');
        await window.secureStore.delete('email');

        // 3) redirect to verify.html with new username
        location.href = `verify.html?username=${encodeURIComponent(newU)}`;
        return;
      }

      // —––– USERNAME ONLY: update in-place –––—
      showToast('Profile updated!', 'info');

      if (newU !== username) {
        await window.secureStore.set('username', newU);
        username = newU;
        userInfoEl.textContent = newU;
      }
      document.getElementById('username').value = newU;

    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // — Disable account —
disableAccountBtn.addEventListener('click', () => {
  // 0) hide the profile modal so our confirm modal sits on top
  profileModal.classList.add('hidden');

  // 1) show your custom confirm
  showModal(
    'Disabling your account will prevent you from logging in until you reactivate via the email we’ll send. Continue?',
    async () => {
      try {
        await submitProfile({ disable: 1, delete: 0 });
        showToast('Account disabled.', 'warning');

        // ─── CLEAR EVERYTHING & REDIRECT ───
        await window.secureStore.delete('session_token');
        await window.secureStore.delete('refresh_token');
        await window.secureStore.delete('username');
        await window.secureStore.delete('email');
        location.href = 'index.html';
      } catch (err) {
        showToast(err.message, 'error');
      }
    }
  );
});

// — Delete account —
deleteAccountBtn.addEventListener('click', () => {
  // 0) hide the profile modal
  profileModal.classList.add('hidden');

  showModal(
    'Warning: This will PERMANENTLY DELETE your account **and all associated data**, including messages and chats. This action cannot be undone. Continue?',
    async () => {
      try {
        await submitProfile({ disable: 0, delete: 1 });
        showToast('Account deleted.', 'error');

        // ─── CLEAR EVERYTHING & REDIRECT ───
        await window.secureStore.delete('session_token');
        await window.secureStore.delete('refresh_token');
        await window.secureStore.delete('username');
        await window.secureStore.delete('email');
        location.href = 'index.html';
      } catch (err) {
        showToast(err.message, 'error');
      }
    }
  );
});

  // 2) Cache DOM elements
  const chatListEl    = document.getElementById('chat-list');
  const messagesEl    = document.getElementById('messages');
  const newChatInput  = document.getElementById('new-chat-username');
  const createChatBtn = document.getElementById('create-chat-btn');
  const messageInput  = document.getElementById('message-text');
  const sendBtn       = document.getElementById('send-btn');
  const logoutBtn     = document.getElementById('logout-btn');
  const placeholder = document.getElementById('no-chat-selected');
  // Group-modal elements & state
  const groupModalNameDisplay  = document.getElementById('group-modal-name-display');
  const groupMemberInput       = document.getElementById('group-member-input');
  const groupAddMemberBtn      = document.getElementById('group-add-member-btn');
  const groupMemberList        = document.getElementById('group-member-list');
  const groupCreateSubmitBtn   = document.getElementById('group-create-submit-btn');
  const groupCancelBtn         = document.getElementById('group-cancel-btn');
  const groupModalClose        = document.getElementById('group-modal-close');
  const groupModal             = document.getElementById('group-modal');
  let   groupMembers           = [];
  const newGroupNameInput       = document.getElementById('new-group-name');
  const createGroupBtn           = document.getElementById('create-group-btn');

  // Chat header & Edit-Members modal
  const chatHeader         = document.getElementById('chat-header');
  const chatTitle          = document.getElementById('chat-title');
  const editMembersBtn     = document.getElementById('edit-members-btn');

  const editMembersModal       = document.getElementById('edit-members-modal');
  const editMemberList         = document.getElementById('edit-member-list');
  const editMemberInput        = document.getElementById('edit-member-input');
  const editMemberAddBtn       = document.getElementById('edit-member-add-btn');
  const editMembersCloseBtn    = document.getElementById('edit-members-close-btn');
  const editMembersModalClose  = document.getElementById('edit-members-modal-close');

  let currentMembers = [];  // will hold usernames for the current group


  let currentChatID = null;
  let ws;
  let chatToDelete = null; // Store the chatID temporarily

  const messageControls = document.querySelector('.chat-controls');
  const typingIndicator = document.getElementById('typing-indicator');

  messageControls.classList.add('hidden');
  document.getElementById('no-chat-selected').style.display = 'block';

  updateSendButtonState();

  // 1) Open modal
editMembersBtn.addEventListener('click', async () => {
  // Fetch current members
  const res = await window.api.request('/chat/get-members', {
    body: JSON.stringify({ session_token: token, chatID: currentChatID })
  });
  currentMembers = Array.isArray(res.response) ? res.response : [];
  // Render list
  editMemberList.innerHTML = '';
  currentMembers.forEach(u => {
    const li = document.createElement('li');
    li.textContent = u;
    const btn = document.createElement('button');
    btn.textContent = '×';
    btn.onclick = async () => {
      await window.api.request('/chat/remove-members', {
        body: JSON.stringify({ session_token: token, chatID: currentChatID, members: [u] })
      });
      li.remove();
    };
    li.append(btn);
    editMemberList.append(li);
  });
  editMembersModal.classList.remove('hidden');
});

  // 2) Add a new member
  editMemberAddBtn.addEventListener('click', async () => {
    const u = editMemberInput.value.trim();
    if (!u) return;
    await window.api.request('/chat/add-members', {
      body: JSON.stringify({ session_token: token, chatID: currentChatID, members: [u] })
    });
    // Append to list
    const li = document.createElement('li');
    li.textContent = u;
    const btn = document.createElement('button');
    btn.textContent = '×';
    btn.onclick = () => li.remove();
    li.append(btn);
    editMemberList.append(li);
    editMemberInput.value = '';
  });

  // 3) Close modal
  [editMembersCloseBtn, editMembersModalClose].forEach(btn =>
    btn.addEventListener('click', () => {
      editMembersModal.classList.add('hidden');
    })
  );


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

  /**
   * Load and render the user’s chat list.
   */
  async function loadChats() {
    try {
      // 1) Fetch chats from the server
      const res = await window.api.request('/chat/fetch-chats', {
        body: JSON.stringify({ session_token: token })
      });
      const chats = Array.isArray(res.response) ? res.response : [];

      // 2) Clear existing list & reset UI
      chatListEl.innerHTML = '';
      messageControls.classList.add('hidden');
      placeholder.style.display = 'block';

      // 3) If no chats, show a friendly placeholder
      if (chats.length === 0) {
        const li = document.createElement('li');
        li.classList.add('chat-entry', 'placeholder');
        li.textContent = 'No conversations yet';
        chatListEl.appendChild(li);
        return;
      }

      // 4) Render each chat
      chats.forEach(({ chatID, name, type }) => {
        const li = document.createElement('li');
        li.classList.add('chat-entry');
        li.dataset.chatId   = chatID;
        li.dataset.username = name;
        li.dataset.type     = type;

        // Chat title area
        const nameWrapper = document.createElement('div');
        nameWrapper.classList.add('chat-name-wrapper');
        const chatName = document.createElement('span');
        chatName.classList.add('chat-name');
        chatName.textContent = name;
        nameWrapper.append(chatName);

        // Delete‐chat button
        const archiveBtn = document.createElement('button');
        archiveBtn.classList.add('archive-chat-btn');
        archiveBtn.title = 'Archive chat';
        archiveBtn.innerHTML = '&#128190;'; // 📁 icon, or use '×' if you prefer
        archiveBtn.addEventListener('click', e => {
          e.stopPropagation();
          handleArchiveChat(chatID);
        });

        // Wrap into a header row
        const header = document.createElement('div');
        header.classList.add('chat-header');
        header.append(nameWrapper, archiveBtn);

        // Assemble
        li.append(header);
        li.addEventListener('click', () => selectChat(chatID));
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
    const modal        = document.getElementById('modal-container');
    const modalMessage = document.getElementById('modal-message');
    const confirmBtn   = document.getElementById('modal-confirm-btn');
    const cancelBtn    = document.getElementById('modal-cancel-btn');
  
    modalMessage.textContent = message;
    modal.classList.remove('hidden');
  
    // Handle Enter → click "No"
    function handleKey(event) {
      if (event.key === 'Enter') {
        event.preventDefault();
        cancelBtn.click();
      }
    }
    document.addEventListener('keydown', handleKey);
  
    confirmBtn.onclick = () => {
      document.removeEventListener('keydown', handleKey);
      modal.classList.add('hidden');
      onConfirm();
    };
  
    cancelBtn.onclick = () => {
      document.removeEventListener('keydown', handleKey);
      modal.classList.add('hidden');
    };
  }
  

  // Add deleteChat function
  async function archiveChat(chatID) {
    try {
      await window.api.request('/chat/archive-chat', {
        body: JSON.stringify({ session_token: token, chatID })
      });
      showToast('Chat archived successfully!', 'info');
      await loadChats();
      // if you’re currently viewing that chat, clear the view:
      if (currentChatID === chatID) selectChat(null);
    } catch (err) {
      console.error('archiveChat error', err);
      showToast(`Could not archive chat: ${err.message || err}`, 'error');
    }
  }

  /**
   * Prompt the user, then archive on confirm.
   */
  async function handleArchiveChat(chatID) {
    showModal(
      'Are you sure you want to archive this chat? You can still rejoin it later.',
      async () => {
        await archiveChat(chatID);
      }
    );
  }

/**
 * Selects a chat by ID:
 *  • Shows or hides the header + Edit-Members button
 *  • Leaves the old room and joins the new one via WS
 *  • Fetches and renders message history
 *  • Highlights the active chat in the sidebar
 */
async function selectChat(chatID) {
  // 1) No selection: clear and hide
  if (!chatID) {
    currentChatID = null;
    messagesEl.innerHTML = '';
    messageControls.classList.add('hidden');
    placeholder.style.display = 'block';
    typingIndicator.style.display = 'none';
    chatHeader.classList.add('hidden');
    return;
  }

  // 2) Grab the corresponding <li> (must do this before using it!)
  const li = chatListEl.querySelector(`li[data-chat-id="${chatID}"]`);
  const name = li?.dataset.username ?? 'Unknown Chat';
  const type = li?.dataset.type     ?? 'private';

  // 3) Show header + set title
  chatHeader.classList.remove('hidden');
  chatTitle.textContent = name;

  // 4) Show Edit-Members only for groups
  if (type === 'group') {
    editMembersBtn.classList.remove('hidden');
  } else {
    editMembersBtn.classList.add('hidden');
  }

  // 5) Reveal message controls
  placeholder.style.display = 'none';
  messageControls.classList.remove('hidden');
  typingIndicator.style.display = 'none';

  // 6) If already in this chat, stop here
  if (currentChatID === chatID) return;

  // 7) Leave old room
  if (currentChatID != null) {
    ws.send(JSON.stringify({ type: 'leave_chat', chatID: currentChatID }));
  }
  currentChatID = chatID;
  messagesEl.innerHTML = '';

  // 8) Join new room
  ws.send(JSON.stringify({ type: 'join_chat', chatID }));

  // 9) Fetch + render history
  try {
    const res = await window.api.request('/chat/messages', {
      body: JSON.stringify({ username, session_token: token, chatID })
    });
    const history = Array.isArray(res.response) ? res.response : [];
    history.forEach(appendMessage);
  } catch (err) {
    console.error('history fetch error', err);
  }

  // 10) Highlight the active chat
  chatListEl.querySelectorAll('li').forEach(el => {
    el.classList.toggle('active', Number(el.dataset.chatId) === chatID);
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

  //  —  Open group-creation modal
  createGroupBtn.addEventListener('click', () => {
    const name = newGroupNameInput.value.trim();
    if (!name) return showToast('Enter a group name','error');
    // show name in modal
    groupModalNameDisplay.textContent = name;
    // reset member list
    groupMembers = [];
    groupMemberList.innerHTML = '';
    // open it
    groupModal.classList.remove('hidden');
  });

  //  —  Close modal (Cancel or ×)
  [groupCancelBtn, groupModalClose].forEach(btn =>
    btn.addEventListener('click', () => {
      groupModal.classList.add('hidden');
    })
  );

  //  —  Add one member to the list
  groupAddMemberBtn.addEventListener('click', () => {
    const user = groupMemberInput.value.trim();
    if (!user) return;
    const lower = user.toLowerCase();
    if (groupMembers.includes(lower)) {
      return showToast(`${user} already added`,'warning');
    }
    groupMembers.push(lower);
    // render it
    const li = document.createElement('li');
    li.textContent = user;
    // remove button
    const rem = document.createElement('button');
    rem.textContent = '×';
    rem.className = 'archive-chat-btn';
    rem.style.marginLeft = '8px';
    rem.onclick = () => {
      groupMembers = groupMembers.filter(u => u !== lower);
      li.remove();
    };
    li.append(rem);
    groupMemberList.append(li);
    groupMemberInput.value = '';
  });

  //  —  Submit the complete group
  groupCreateSubmitBtn.addEventListener('click', async () => {
    const name = newGroupNameInput.value.trim();
    if (!name) return showToast('Enter a group name','error');
    if (groupMembers.length === 0) return showToast('Add at least one member','error');
    try {
      const res = await window.api.request('/chat/create-group', {
        body: JSON.stringify({
          session_token: token,
          name,
          members: groupMembers
        })
      });
      const newChatID = res.response.chatID;
      showToast('Group created!','info');
      // close & reset
      groupModal.classList.add('hidden');
      newGroupNameInput.value = '';
      // refresh and join
      await loadChats();
      selectChat(newChatID);
    } catch (err) {
      console.error(err);
      showToast('Failed to create group: ' + (err.message||err),'error');
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