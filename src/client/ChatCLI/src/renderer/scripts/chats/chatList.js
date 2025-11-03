import { store } from '../core/store.js';
import { apiRequest } from '../core/api.js';
import { showToast } from '../ui/toasts.js';
import { renderArchivedChats } from './archive.js';
import { selectChat } from './chatSession.js';

// Creates a chat item element for the chat list
export function createChatItem(chatID, name, type) {
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
    window.dispatchEvent(new CustomEvent('chat:archive', { detail: { chatID } }));
  });
  chatItem.append(chatClose);

  chatItem.addEventListener('click', () => selectChat(chatID));
  return chatItem;
}

// Loads chats from the server and populates the chat list
export async function loadChats() {
  const { token } = store;
  const { chatListEl, placeholder } = store.refs;

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

    // Populate chat list
    const frag = document.createDocumentFragment();
    chats.forEach(({ chatID, name, type }) => {
      frag.appendChild(createChatItem(chatID, name, type));
    });
    chatListEl.appendChild(frag);

    const archivedChats = await apiRequest('/chat/fetch-archived', {
      body: JSON.stringify({ session_token: token })
    });
    store.archivedChatsData = Array.isArray(archivedChats) ? archivedChats : [];

    if (store.archivedChatsData.length > 0) {
      const toggleContainer = document.createElement('div');
      toggleContainer.style.textAlign = 'center';
      toggleContainer.style.margin = '16px 0';

      const toggleBtn = document.createElement('button');
      toggleBtn.className = 'archived-chats-button';
      toggleBtn.textContent = store.archivedVisible ? '📂 Hide Archived Chats' : '📁 Show Archived Chats';
      toggleBtn.addEventListener('click', () => {
        store.archivedVisible = !store.archivedVisible;
        toggleBtn.textContent = store.archivedVisible ? '📂 Hide Archived Chats' : '📁 Show Archived Chats';
        renderArchivedChats();
      });

      toggleContainer.append(toggleBtn);
      chatListEl.append(toggleContainer);
    }

    renderArchivedChats();
    if (store.archivedVisible) renderArchivedChats();

  } catch (err) {
    console.error('loadChats error:', err);
    showToast('Failed to load chats: ' + err.message, 'error');
  }
}

export async function onWSChatCreated({ detail : msg }) {
  loadChats();
}