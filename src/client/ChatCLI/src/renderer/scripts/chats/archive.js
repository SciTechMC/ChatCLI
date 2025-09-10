import { store } from '../core/store.js';
import { apiRequest } from '../core/api.js';
import { showToast } from '../ui/toasts.js';
import { selectChat } from './chatSession.js';

export function renderArchivedChats() {
  const { chatListEl } = store.refs;
  chatListEl.querySelectorAll('.chat-item.archived').forEach(el => el.remove());
  if (!store.archivedVisible) return;

  store.archivedChatsData.forEach(({ chatID, name, type }) => {
    const item = document.createElement('div');
    item.classList.add('chat-item', 'archived');
    item.dataset.chatId = chatID;
    item.dataset.username = name;
    item.dataset.type = type;

    const info = document.createElement('div');
    info.classList.add('chat-info');
    const chatName = document.createElement('div');
    chatName.classList.add('chat-name');
    chatName.textContent = name;
    info.appendChild(chatName);
    item.appendChild(info);

    const unarchiveBtn = document.createElement('div');
    unarchiveBtn.classList.add('chat-close');
    unarchiveBtn.title = 'Unarchive';
    unarchiveBtn.innerHTML = '⤴';
    unarchiveBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      try {
        await apiRequest('/chat/unarchive-chat', {
          body: JSON.stringify({ session_token: store.token, chatID })
        });
        showToast('Chat unarchived successfully!', 'info');
        store.archivedVisible = false;
        await window.dispatchEvent(new CustomEvent('chat:reload'));
        if (store.currentChatID === chatID) selectChat(null);
      } catch (err) {
        console.error('Unarchive error:', err);
        showToast(err.message || 'Could not unarchive chat', 'error');
      }
    });
    item.appendChild(unarchiveBtn);

    item.addEventListener('click', () => selectChat(chatID));
    store.refs.chatListEl.appendChild(item);
  });
}

export async function archiveChat(chatID) {
  try {
    await apiRequest('/chat/archive-chat', {
      body: JSON.stringify({ session_token: store.token, chatID })
    });
    showToast('Chat archived successfully!', 'info');
    await window.dispatchEvent(new CustomEvent('chat:reload'));
    if (store.currentChatID === chatID) selectChat(null);
  } catch (err) {
    console.error('archiveChat error:', err);
    showToast(`Could not archive chat: ${err.message || 'Unknown error'}`, 'error');
  }
}

export function handleArchiveChat(chatID) {
  window.dispatchEvent(new CustomEvent('chat:confirm-archive', { detail: { chatID } }));
}
