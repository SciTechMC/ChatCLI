import { store } from '../core/store.js';
import { showToast } from '../ui/toasts.js';

let ws;
let isConnecting = false;

// ---- Reconnect backoff (unbounded, capped at MAX) ----
let reconnectAttempts = 0;
const BACKOFF_BASE = 1000;        // 1s
const BACKOFF_MAX  = 30000;       // 30s cap

// ---- Heartbeat ----
let hbInterval = null;
let hbTimeout  = null;
const HEARTBEAT_EVERY   = 25000;  // send ping every 25s
const HEARTBEAT_DEAD_MS = 10000;  // if no pong (or any msg) in 10s, kill sock

function clearHeartbeat() {
  if (hbInterval) { clearInterval(hbInterval); hbInterval = null; }
  if (hbTimeout)  { clearTimeout(hbTimeout);   hbTimeout = null; }
}
function armHeartbeat() {
  clearHeartbeat();
  // treat ANY inbound message as liveness
  const markAlive = () => {
    if (hbTimeout) { clearTimeout(hbTimeout); hbTimeout = null; }
    hbTimeout = setTimeout(() => {
      try { ws?.close(); } catch {}
    }, HEARTBEAT_DEAD_MS);
  };
  markAlive();
  hbInterval = setInterval(() => {
    try {
      ws?.send(JSON.stringify({ type: 'ping', ts: Date.now() }));
      // if server doesn't send 'pong', any message still resets the timer via onmessage
      markAlive();
    } catch {
      // if send fails, the socket is already dead; let onclose handle it
    }
  }, HEARTBEAT_EVERY);
}

function nextDelay() {
  const raw = Math.min(BACKOFF_MAX, BACKOFF_BASE * 2 ** reconnectAttempts);
  // jitter 80–120%
  return Math.floor(raw * (0.8 + Math.random() * 0.4));
}

function shouldHoldReconnect() {
  // Don’t hammer while offline or tab hidden (common cause of ERR_NETWORK_IO_SUSPENDED)
  if (navigator && 'onLine' in navigator && !navigator.onLine) return true;
  if (document && typeof document.hidden === 'boolean' && document.hidden) return true;
  return false;
}

function scheduleReconnect(reason = '') {
  if (shouldHoldReconnect()) return; // will be resumed by visibility/online handler
  const delay = nextDelay();
  reconnectAttempts++;
  setTimeout(connectWS, delay);
}

export function connectWS() {
  if (isConnecting || (ws && ws.readyState === WebSocket.OPEN)) return;
  if (shouldHoldReconnect()) return; // wait until visible/online

  isConnecting = true;
  try {
    ws = new WebSocket(window.api.WS_URL);
  } catch (e) {
    isConnecting = false;
    scheduleReconnect('ctor-failed');
    return;
  }

  ws.addEventListener('open', () => {
    reconnectAttempts = 0;
    isConnecting = false;

    // auth + idle join (your existing behavior)
    ws.send(JSON.stringify({ type: 'auth', token: store.token }));
    ws.send(JSON.stringify({ type: 'join_idle' }));

    // start heartbeat
    armHeartbeat();
  });

  ws.addEventListener('close', () => {
    isConnecting = false;
    clearHeartbeat();
    scheduleReconnect('close');
  });

  ws.addEventListener('message', (event) => {
    // liveness: any message counts
    if (hbTimeout) { clearTimeout(hbTimeout); hbTimeout = null; }
    hbTimeout = setTimeout(() => {
      try { ws?.close(); } catch {}
    }, HEARTBEAT_DEAD_MS);
  
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch (e) {
      console.error('Bad WS JSON:', e, event.data);
      return;
    }
  
    // optional: explicit pong from server
    if (msg.type === 'pong') return;
  
    // 🔔 Global incoming call → raise a UI event for main.js
    if (msg.type === 'incoming_call') {
      const me = (store.username || '').toLowerCase();
      if ((msg.caller || '').toLowerCase() === me) return;
    
      window.dispatchEvent(new CustomEvent('call:global-incoming', {
        detail: { chatID: msg.chatID, caller: msg.caller, startedAt: msg.startedAt }
      }));
      return;
    }
    
  
    if (msg.type === 'auth_ack') return;
  
    if (msg.type === 'new_message') {
      if (store.seenMessageIDs.has(msg.messageID)) return;
      store.seenMessageIDs.add(msg.messageID);
      window.dispatchEvent(new CustomEvent('chat:new-message', { detail: msg }));
      return;
    }
  
    if (msg.type === 'error' && msg.message?.includes('Invalid credentials')) {
      try { ws.close(); } catch {}
      return;
    }
  
    if (msg.type === 'user_typing' && msg.chatID === store.currentChatID &&
        msg.username.toLowerCase() !== (store.username || '').toLowerCase()) {
      window.dispatchEvent(new CustomEvent('chat:user-typing', { detail: msg.username }));
      return;
    }
  
    if (msg.type === 'user_status') {
      window.dispatchEvent(new CustomEvent('chat:user-status', { detail: msg }));
      return;
    }
  });  

  ws.addEventListener('error', (error) => {
    // This will still fire for ERR_NETWORK_IO_SUSPENDED; we just back off calmly.
    console.error('WebSocket error:', error);
    isConnecting = false;
    clearHeartbeat();
    showToast('Connection issue. Reconnecting…', 'error');
    // Let 'close' handler scheduleReconnect; if it doesn't fire, do it here as a fallback:
    scheduleReconnect('error');
  });
}

// Keep your existing API
export function chatSend(payload) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
  }
}

// ---- Resume logic: when the user returns or network is back, attempt reconnect now
function resumeIfNeeded() {
  if (ws && ws.readyState === WebSocket.OPEN) return;
  reconnectAttempts = Math.max(0, reconnectAttempts - 1); // be gentle after a resume
  connectWS();
}

window.addEventListener('online', resumeIfNeeded);
window.addEventListener('focus', resumeIfNeeded);
window.addEventListener('visibilitychange', () => { if (!document.hidden) resumeIfNeeded(); });
window.addEventListener('pageshow', resumeIfNeeded); // fired after bfcache restore on some browsers
