import { store } from '../core/store.js';
import { showToast } from '../ui/toasts.js';

let ws;
let isConnecting = false;
let reconnectAttempts = 0;
const maxRetries = 5;

export function connectWS() {
  if (isConnecting || (ws && ws.readyState === WebSocket.OPEN)) return;

  isConnecting = true;
  ws = new WebSocket(window.api.WS_URL);

  ws.addEventListener('open', () => {
    reconnectAttempts = 0;
    isConnecting = false;
    ws.send(JSON.stringify({ type: 'auth', token: store.token }));
    ws.send(JSON.stringify({ type: 'join_idle' }));
  });

  ws.addEventListener('close', () => {
    isConnecting = false;
    if (reconnectAttempts < maxRetries) {
      const delay = Math.pow(2, reconnectAttempts) * 1000 * (0.8 + Math.random() * 0.4);
      setTimeout(connectWS, delay);
      reconnectAttempts++;
    }
  });

  ws.addEventListener('message', (event) => {
    const msg = JSON.parse(event.data);

    if (msg.type === 'auth_ack') return;

    if (msg.type === 'new_message') {
      if (store.seenMessageIDs.has(msg.messageID)) return;
      store.seenMessageIDs.add(msg.messageID);
      window.dispatchEvent(new CustomEvent('chat:new-message', { detail: msg }));
      return;
    }

    if (msg.type === 'error' && msg.message?.includes('Invalid credentials')) {
      ws.close();
    }

    if (msg.type === 'user_typing' && msg.chatID === store.currentChatID && msg.username.toLowerCase() !== (store.username || '').toLowerCase()) {
      window.dispatchEvent(new CustomEvent('chat:user-typing', { detail: msg.username }));
    }

    if (msg.type === 'user_status') {
      window.dispatchEvent(new CustomEvent('chat:user-status', { detail: msg }));
    }
  });

  ws.addEventListener('error', (error) => {
    console.error('WebSocket error:', error);
    isConnecting = false;
    showToast('Connection error. Reconnecting...', 'error');
  });
}

export function chatSend(payload) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
  }
}
