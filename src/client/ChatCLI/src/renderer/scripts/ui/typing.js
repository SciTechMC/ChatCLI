import { store } from '../core/store.js';

export function initTypingIndicator() {
  const typingIndicator = document.createElement('div');
  typingIndicator.id = 'typing-indicator';
  typingIndicator.style.display = 'none';
  typingIndicator.style.fontSize = '12px';
  typingIndicator.style.color = 'var(--text-secondary)';
  const chatArea  = document.querySelector('.chat-area');
  const chatInput = document.querySelector('.chat-input');
  chatArea.insertBefore(typingIndicator, chatInput);
  store.refs.typingIndicator = typingIndicator;
}

export function updateTypingIndicator() {
  const typingIndicator = store.refs.typingIndicator;
  if (!typingIndicator) return;

  if (store.typingUsers.size === 0) {
    typingIndicator.style.display = 'none';
    return;
  }
  const users = Array.from(store.typingUsers);
  let text;
  if (users.length === 1)      text = `${users[0]} is typing...`;
  else if (users.length === 2) text = `${users[0]} and ${users[1]} are typing...`;
  else {
    const last = users.pop();
    text = `${users.join(', ')}, and ${last} are typing...`;
  }
  typingIndicator.textContent = text;
  typingIndicator.style.display = 'block';
}
