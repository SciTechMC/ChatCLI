import { store } from '../core/store.js';
import { apiRequest } from '../core/api.js';
import { showToast } from '../ui/toasts.js';
import { showConfirmationModal } from '../ui/modals.js';
import { connectWS, chatSend } from '../sockets/chatSocket.js';
import { updateTypingIndicator } from '../ui/typing.js';
import { loadChats } from './chatList.js';
import { loadGroupMembers } from './groupService.js';
import { connectCallWS } from '../calls/callSockets.js';

const MAX_MESSAGE_LEN = 2048;

export function updateSendButtonState() {
  const { messageInput, sendBtn } = store.refs;
  const hasContent = messageInput.value.trim().length > 0;
  sendBtn.classList.toggle('disabled', !hasContent);
  sendBtn.disabled = !hasContent;
}

export async function selectChat(chatID) {
  const {
    messagesEl, chatTitle, editMembersBtn
  } = store.refs;

  if (!chatID) {
    store.currentChatID = null;
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
    if (editMembersBtn) editMembersBtn.style.display = 'none';
    return;
  }

  chatID = parseInt(chatID, 10);

  if (store.refs.btnStartCall) store.refs.btnStartCall.disabled = !chatID;
  if (store.refs.btnLeave)     store.refs.btnLeave.disabled     = true;
  if (store.refs.btnMute)      store.refs.btnMute.disabled      = true;

  const chatItem = store.refs.chatListEl.querySelector(`[data-chat-id="${chatID}"]`);
  if (!chatItem) {
    console.error('Chat item not found');
    return;
  }

  const name = chatItem.dataset.username || 'Unknown Chat';
  const type = chatItem.dataset.type || 'private';

  document.querySelector('.chat-header').style.display = 'flex';
  chatTitle.textContent = name;
  if (type === 'group' && store.refs.editMembersBtn) {
    store.refs.editMembersBtn.style.display = 'block';
  } else if (store.refs.editMembersBtn) {
    store.refs.editMembersBtn.style.display = 'none';
  }
  document.querySelector('.chat-input').classList.remove('hidden');
  store.refs.typingIndicator.style.display = 'none';

  // Clear typing state
  store.typingUsers.clear();
  store.typingTimeouts.forEach(timeout => clearTimeout(timeout));
  store.typingTimeouts.clear();

  // leave previous chat
  if (store.currentChatID != null) {
    chatSend({ type: 'leave_chat', chatID: store.currentChatID });
  }

  store.currentChatID = chatID;
  store.refs.messagesEl.innerHTML = '';

  chatSend({ type: 'join_chat', chatID });

  if (type === 'group') {
    loadGroupMembers(chatID);
    if (store.refs.editMembersBtn) store.refs.editMembersBtn.style.display = 'block';
  } else if (store.refs.editMembersBtn) {
    store.refs.editMembersBtn.style.display = 'none';
  }

  try {
    const history = await apiRequest('/chat/messages', {
      body: JSON.stringify({ session_token: store.token, chatID })
    });
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

  if (store.currentChatID && store.username) {
    connectCallWS(); // signaling WS for calls
  }
}

export function appendMessage({ username: msgUser, message, timestamp }) {
  const { messagesEl } = store.refs;
  const messageDiv = document.createElement('div');
  messageDiv.classList.add('message');

  const header = document.createElement('div');
  header.className = 'message-header';

  const userEl = document.createElement('span');
  userEl.classList.add('message-sender');
  if (msgUser.toLowerCase() === (store.username || '').toLowerCase()) {
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

export async function sendMessage() {
  const { messageInput, charCounter } = store.refs;
  if (!store.currentChatID) {
    return showToast('Select a chat first.', 'error');
  }
  const text = messageInput.value.trim();
  if (!text) return;

  const len = text.length;
  if (len > MAX_MESSAGE_LEN) {
    showConfirmationModal(
      `Your message is ${len} characters long and will be split into ${Math.ceil(len / MAX_MESSAGE_LEN)} messages. Continue?`,
      'Split Message?',
      async () => {
        const chunks = [];
        let start = 0;
        while (start < text.length) {
          let end = Math.min(text.length, start + MAX_MESSAGE_LEN);
          if (end < text.length) {
            const lastSpace = text.lastIndexOf(' ', end);
            if (lastSpace > start) end = lastSpace;
          }
          chunks.push(text.slice(start, end));
          start = end;
        }
        for (const chunk of chunks) {
          chatSend({ type: 'post_msg', chatID: store.currentChatID, text: chunk });
        }
        messageInput.value = '';
        messageInput.style.height = 'auto';
        updateSendButtonState();
        charCounter.style.display = 'none';
      }
    );
    return;
  }

  chatSend({ type: 'post_msg', chatID: store.currentChatID, text });

  messageInput.value = '';
  messageInput.style.height = 'auto';
  updateSendButtonState();
  charCounter.style.display = 'none';
}

// WS event handlers (hooked by main.js)
export function onWSNewMessage({ detail: msg }) {
  if (msg.chatID === store.currentChatID) {
    appendMessage({
      username: msg.username,
      message: msg.message,
      timestamp: msg.timestamp
    });
  } else {
    const preview = store.refs.chatListEl
      .querySelector(`.chat-item[data-chat-id="${msg.chatID}"] .chat-preview`);
    if (preview) preview.textContent = msg.message.slice(0, 50);
  }
}

export function onWSTyping({ detail: username }) {
  if (username.toLowerCase() === (store.username || '').toLowerCase()) return;
  const user = username;
  store.typingUsers.add(user);
  clearTimeout(store.typingTimeouts.get(user));
  store.typingTimeouts.set(user, setTimeout(() => {
    store.typingUsers.delete(user);
    updateTypingIndicator();
  }, 3000));
  updateTypingIndicator();
}

export function onWSUserStatus({ detail: msg }) {
  const chatItems = document.querySelectorAll(`.chat-item[data-username="${msg.username}"]`);
  chatItems.forEach(el => {
    const statusIndicator = el.querySelector('.chat-status');
    if (statusIndicator) {
      statusIndicator.classList.toggle('online', msg.online);
      statusIndicator.classList.toggle('offline', !msg.online);
    }
  });
}
