import { store } from '../core/store.js';
import { showToast } from '../ui/toasts.js';
import { joinCall, startCall } from '../calls/rtc.js';
import { openCallWS } from '../calls/callSockets.js';

let ws;
let isConnecting = false;

// ---- Reconnect backoff (unbounded, capped at MAX) ----
let reconnectAttempts = 0;
const BACKOFF_BASE = 1000;        // 1s
const BACKOFF_MAX  = 15000;       // 15s cap

// ---------- Utility: reconnect scheduling ----------
function nextDelay() {
  const raw = Math.min(BACKOFF_MAX, BACKOFF_BASE * 2 ** reconnectAttempts);
  // jitter 80–120%
  return Math.floor(raw * (0.8 + Math.random() * 0.4));
}

function shouldHoldReconnect() {
  // Don’t hammer while offline or tab hidden
  if (navigator && 'onLine' in navigator && !navigator.onLine) return true;
  if (document && typeof document.hidden === 'boolean' && document.hidden) return true;
  return false;
}

function scheduleReconnect(reason = '') {
  if (shouldHoldReconnect()) return;
  const delay = nextDelay();
  reconnectAttempts++;
  console.warn(`[CHAT-WS] Reconnecting in ${delay}ms (${reason})`);
  setTimeout(connectWS, delay);
}

// ---------- Main connect ----------
export function connectWS() {
  if (isConnecting || (ws && ws.readyState === WebSocket.OPEN)) return;
  if (shouldHoldReconnect()) return;

  isConnecting = true;
  try {
    ws = new WebSocket(window.api.WS_URL);
    store.WS_URL = window.api.WS_URL;
    store.ws = ws;
  } catch (e) {
    isConnecting = false;
    scheduleReconnect('ctor-failed');
    return;
  }

  ws.addEventListener('open', () => {
    reconnectAttempts = 0;
    isConnecting = false;
    console.log('[CHAT-WS] Connected ✅');

    if (store.token) {
      ws.send(JSON.stringify({ type: 'auth', token: store.token }));
    }
    ws.send(JSON.stringify({ type: 'join_idle' }));
  });

  ws.addEventListener('close', () => {
    console.warn('[CHAT-WS] Closed ❌');
    isConnecting = false;
    scheduleReconnect('close');
  });

  ws.addEventListener('error', (error) => {
    console.error('[CHAT-WS] Error', error);
    isConnecting = false;
    showToast('Connection issue. Reconnecting…', 'error');
    scheduleReconnect('error');
  });

  // ---------- Main message handler (ASYNC) ----------
  ws.addEventListener('message', async (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      console.warn('[CHAT-WS] Bad JSON', event.data);
      return;
    }

    console.log('[CHAT-WS]', msg);

    // Chat messages
    if (msg.type === 'new_message') {
      if (store.seenMessageIDs.has(msg.messageID)) return;
      store.seenMessageIDs.add(msg.messageID);
      window.dispatchEvent(new CustomEvent('chat:new-message', { detail: msg }));
      return;
    }

    if (msg.type === 'user_typing' &&
        msg.chatID === store.currentChatID &&
        msg.username.toLowerCase() !== (store.username || '').toLowerCase()) {
      window.dispatchEvent(new CustomEvent('chat:user-typing', { detail: msg.username }));
      return;
    }

    if (msg.type === 'user_status') {
      window.dispatchEvent(new CustomEvent('chat:user-status', { detail: msg }));
      return;
    }

    // Call signaling (global)
    if (msg.type === 'call_incoming') {
      console.log('[CALL-INCOMING]', msg);
      window.dispatchEvent(new CustomEvent('call:incoming', {
        detail: { chatID: msg.chatID, from: msg.from, call_id: msg.call_id }
      }));
      showToast(`${msg.from || 'Someone'} is calling…`, 'info');
      return;
    }

    if (msg.type === 'call_state') {
      console.log('[CALL-STATE]', msg);
      if (msg.state === 'ringing') {
        window.dispatchEvent(new CustomEvent('call:incoming', {
          detail: { chatID: msg.chatID, from: msg.from, call_id: msg.call_id }
        }));
        return;
      }
      if (msg.state === 'accepted') {
        if (store.call._startedForCallId === msg.call_id) return;
        store.call._startedForCallId = msg.call_id;
        const allowed = (store.callState === 'incoming' || store.callState === 'outgoing');
        if (!allowed) return;
        if (store.call.currentCallId && store.call.currentCallId !== msg.call_id) return;
        if (!store.call.currentCallId) store.call.currentCallId = msg.call_id;
        if (msg.call_id) openCallWS(msg.call_id, store.username);
        const iAmCaller = (store.username || '').toLowerCase() === (msg.from || '').toLowerCase();
        if (iAmCaller) await startCall(); else await joinCall();
        store.callState = 'in-call';
        store.callActiveChatID = msg.chatID;
        window.dispatchEvent(new Event('call:connected'));
        return;
      }
      return;
    }

    if (msg.type === 'call_accepted') {
      if (store.call._startedForCallId === msg.call_id) return;
      store.call._startedForCallId = msg.call_id;
      if (msg.call_id) { store.call.currentCallId = msg.call_id; openCallWS(msg.call_id, store.username); }
      const iAmCaller = (store.username || '').toLowerCase() === (msg.from || '').toLowerCase();
      if (iAmCaller) await startCall(); else await joinCall();
      store.callState = 'in-call';
      store.callActiveChatID = msg.chatID;
      window.dispatchEvent(new Event('call:connected'));
      return;
    }

    if (msg.type === 'call_declined' || msg.type === 'call_ended') {
      console.log('[CALL-ENDED/DECLINED]', msg);
      window.dispatchEvent(new Event('call:ended'));
      return;
    }
  });
}


// ---------- Sending ----------
export function chatSend(payload) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
  } else {
    console.warn('[CHAT-WS] send() called while not open', payload);
  }
}

// ---------- Resume logic ----------
function resumeIfNeeded() {
  if (ws && ws.readyState === WebSocket.OPEN) return;
  reconnectAttempts = Math.max(0, reconnectAttempts - 1);
  connectWS();
}

export function initChatSocketAutoResume() {
  window.addEventListener('online', resumeIfNeeded);
  window.addEventListener('focus', resumeIfNeeded);
  window.addEventListener('visibilitychange', () => { if (!document.hidden) resumeIfNeeded(); });
  window.addEventListener('pageshow', resumeIfNeeded);
}