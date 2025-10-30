import { store } from '../core/store.js';
import { setRemoteOffer, setRemoteAnswer, endCall } from './rtc.js';

/** ---- small helpers ---- */
function ensureCallState() {
  store.call ??= {};
  store.call.queue ??= [];
  store.call.iceServers ??= [{ urls: 'stun:stun.l.google.com:19302' }];
}

/** Queue-or-send signaling messages (WebRTC-level) */
export function callSend(obj) {
  ensureCallState();
  const ws = store.call.callWS;
  console.log('[CALL] Sending signal:', obj.type, obj);
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(obj));
  } else {
    console.log('[CALL] Queuing signal - WS not ready');
    store.call.queue.push(obj);
  }
}

function flushQueue() {
  const ws = store.call.callWS;
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  if (!store.call.queue?.length) return;
  console.log('[CALL] Flushing queued signals:', store.call.queue.length);
  for (const msg of store.call.queue) {
    console.log('[CALL] Sending queued signal:', msg.type);
    ws.send(JSON.stringify(msg));
  }
  store.call.queue.length = 0;
}

/** ---- app-level signaling helpers (invite / accept / decline / end) ---- */
export function sendCallInvite({ chatID, callee }) {
  const ws = store.call?.callWS;
  if (!ws || ws.readyState !== WebSocket.OPEN) return console.warn('[CALL] WS not open for call_invite');
  ws.send(JSON.stringify({ type: 'call_invite', chatID, callee }));
}

export function sendCallAccept(chatID) {
  const ws = store.call?.callWS;
  if (!ws || ws.readyState !== WebSocket.OPEN) return console.warn('[CALL] WS not open for call_accept');
  ws.send(JSON.stringify({ type: 'call_accept', chatID }));
}

export function sendCallDecline(chatID) {
  const ws = store.call?.callWS;
  if (!ws || ws.readyState !== WebSocket.OPEN) return console.warn('[CALL] WS not open for call_decline');
  ws.send(JSON.stringify({ type: 'call_decline', chatID }));
}

export function sendCallEnd(chatID) {
  const ws = store.call?.callWS;
  if (!ws || ws.readyState !== WebSocket.OPEN) return console.warn('[CALL] WS not open for call_end');
  ws.send(JSON.stringify({ type: 'call_end', chatID }));
}

/** Ensure the call WS is OPEN */
export async function ensureCallWSOpen() {
  console.log('[CALL] Ensuring WebSocket connection.');
  if (store.call.callWS?.readyState === WebSocket.OPEN) {
    console.log('[CALL] WebSocket already open');
    return;
  }
  connectCallWS();
  await new Promise((resolve, reject) => {
    const ws = store.call.callWS;
    if (!ws) return reject(new Error('No call WS'));
    const onOpen = () => { ws.removeEventListener('open', onOpen); resolve(); };
    const onErr  = (e) => { ws.removeEventListener('error', onErr); reject(e); };
    ws.addEventListener('open', onOpen);
    ws.addEventListener('error', onErr);
  });
}

/** Create (or reconnect) the per-chat call WebSocket */
export function connectCallWS() {
  ensureCallState();

  const { currentChatID, username, token } = store;
  if (!currentChatID || !username) {
    return;
  }

  // close an existing socket if it's CONNECTING or OPEN
  if (store.call.callWS && store.call.callWS.readyState <= 1) {
    try { store.call.callWS.close(); } catch {}
  }

  const base = new URL(window.api.WS_URL);
  // keep your /ws/{chatID}/{username} pattern (server accepts typed messages too)
  base.pathname = base.pathname.replace(/\/?ws$/, '') + `/ws/${currentChatID}/${encodeURIComponent(username)}`;
  const callUrl = base.href;

  const ws = new WebSocket(callUrl);
  store.call.callWS = ws;

  ws.onopen = () => {
    console.log('[CALL] WebSocket opened successfully');
    ws.send(JSON.stringify({ type: 'join_chat', chatID: currentChatID }));
    flushQueue();
  };

  ws.onclose = () => {
    console.log('[CALL] WebSocket connection closed');
  };
  
  ws.onerror = (e) => console.error('[CALL] WebSocket error:', e);

  ws.onmessage = async (ev) => {
    const msg = JSON.parse(ev.data);
    console.log('[CALL] Received signal:', msg.type, msg);

    const msgChatID = msg.chatID ?? store.currentChatID;

    /** -------- app-level call messages from the backend -------- */

    if (msg.type === 'call_incoming') {
      window.dispatchEvent(new CustomEvent('call:incoming', {
        detail: { chatID: msgChatID, from: msg.from }
      }));
      return;
    }

    if (msg.type === 'call_state') {
      if (msg.state === 'ringing') {
        window.dispatchEvent(new CustomEvent('call:incoming', {
          detail: { chatID: msgChatID, from: msg.from }
        }));
      } else if (msg.state === 'accepted') {
        window.dispatchEvent(new Event('call:connected'));
      }
      return;
    }

    if (msg.type === 'call_accepted') {
      window.dispatchEvent(new Event('call:connected'));
      return;
    }

    if (msg.type === 'call_declined') {
      window.dispatchEvent(new Event('call:ended'));
      return;
    }

    if (msg.type === 'call_ended') {
      window.dispatchEvent(new Event('call:ended'));
      return;
    }

    /** -------- Per-chat WebRTC signaling -------- */

    if (msg.type === 'call-started' && !store.call.inCall) {
      console.log('[CALL] New call started by:', msg.from);
      window.dispatchEvent(new CustomEvent('call:incoming', {
        detail: { chatID: msgChatID, from: msg.from }
      }));
      return;
    }

    // Caller sends an SDP offer
    if (msg.type === 'offer') {
      console.log('[CALL] Received offer, joining armed:', store.call.joiningArmed);
      if (!store.call.joiningArmed) {
        console.log('[CALL] Storing pending offer');
        store.call.pendingOffer = msg.sdp;
        window.dispatchEvent(new CustomEvent('call:incoming', {
          detail: { chatID: msgChatID, from: msg.from }
        }));
        return;
      }
      await setRemoteOffer(msg.sdp);
      console.log('[CALL] Set remote offer and enabled controls');
      store.call.inCall = true;
      window.dispatchEvent(new Event('call:started'));
      return;
    }

    if (msg.type === 'answer') {
      console.log('[CALL] Received answer, signaling state:', store.call.pc?.signalingState);
      if (store.call.pc && store.call.pc.signalingState === 'have-local-offer') {
        await setRemoteAnswer(msg.sdp);
        console.log('[CALL] Set remote answer');
        window.dispatchEvent(new Event('call:answer'));
      }
      return;
    }

    // ICE
    if (msg.type === 'ice-candidate' && store.call.pc && msg.candidate) {
      console.log('[CALL] Received ICE candidate:', msg.candidate.candidate);
      try {
        await store.call.pc.addIceCandidate(new RTCIceCandidate(msg.candidate));
        console.log('[CALL] Added ICE candidate successfully');
      } catch (e) {
        console.error('[CALL] ICE candidate addition failed:', e);
      }
      return;
    }

    if (msg.type === 'leave') {
      console.log('[CALL] Peer left the call');
      endCall('Peer left');
      return;
    }
  };
}