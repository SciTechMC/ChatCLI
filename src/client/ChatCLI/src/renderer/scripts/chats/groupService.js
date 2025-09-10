import { store } from '../core/store.js';
import { apiRequest } from '../core/api.js';
import { showToast } from '../ui/toasts.js';

export async function loadGroupMembers(chatID) {
  try {
    const { members } = await apiRequest('/chat/get-members',
      { body: JSON.stringify({ session_token: store.token, chatID }) });
    const list = store.refs.groupMemberList || document.querySelector('#groupEditorModal .user-list');
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
