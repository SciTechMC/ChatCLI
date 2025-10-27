import { store } from '../core/store.js';
import { setRemoteOffer, setRemoteAnswer, endCall } from './rtc.js';

/** ---- small helpers ---- */
function ensureCallState() {
  store.call ??= {};
  store.call.queue ??= [];            // queue ALL signaling until WS is OPEN
  store.call.iceServers ??= [{ urls: 'stun:stun.l.google.com:19302' }];
}

export function setStatus(text, cls = '') {
  const el = store.refs?.statusEl;
  if (el) {
    el.textContent = text;
    el.className = 'status ' + cls;
  }
  console.log('[CALL] Status:', text, `(${cls})`);
}

/** Queue-or-send signaling messages */
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

/** Ensure the call WS is OPEN (returns after 'open') */
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
  console.log('[CALL] Initializing call WebSocket');

  const { currentChatID, username, token } = store;
  if (!currentChatID || !username) {
    setStatus('Missing chat or username for call', 'warn');
    return;
  }

  // close an existing socket if it's CONNECTING or OPEN
  if (store.call.callWS && store.call.callWS.readyState <= 1) {
    console.log('[CALL] Closing existing WebSocket connection');
    try { store.call.callWS.close(); } catch {}
  }

  // Base WS from preload (window.api.WS_URL like ws://host:8765/ws)
  const base = new URL(window.api.WS_URL);
  base.pathname = base.pathname.replace(/\/?ws$/, '') + `/ws/${currentChatID}/${encodeURIComponent(username)}`;
  const callUrl = base.href;

  const ws = new WebSocket(callUrl);
  store.call.callWS = ws;

  ws.onopen = () => {
    console.log('[CALL] WebSocket opened successfully');
    // Optional: auth/handshake if your server expects it
    if (token) {
      console.log('[CALL] Sending authentication');
      ws.send(JSON.stringify({
        type: 'auth',
        token,
        chatID: currentChatID,
        username
      }));
    }
    setStatus('Call WS connected ✅', 'ok');
    flushQueue();
  };

  ws.onclose = () => {
    console.log('[CALL] WebSocket connection closed');
    setStatus('Call WS closed ❌', 'warn');
  };
  
  ws.onerror = (e) => console.error('[CALL] WebSocket error:', e);

  ws.onmessage = async (ev) => {
    const msg = JSON.parse(ev.data);
    console.log('[CALL] Received signal:', msg.type, msg);

    // Someone started a call in this chat — prompt to join if you're not in-call yet
    if (msg.type === 'call-started' && !store.call.inCall) {
      console.log('[CALL] New call started by:', msg.from);
      setStatus(`${msg.from || 'Peer'} started a call — click Join`, 'ok');
      window.dispatchEvent(new Event('call:incoming'));
      return;
    }

    // Caller sends an SDP offer
    if (msg.type === 'offer') {
      console.log('[CALL] Received offer, joining armed:', store.call.joiningArmed);
      if (!store.call.joiningArmed) {
        console.log('[CALL] Storing pending offer');
        store.call.pendingOffer = msg.sdp;
        setStatus('Incoming call — click Join', 'ok');
        window.dispatchEvent(new Event('call:incoming'));
        return;
      }
      await setRemoteOffer(msg.sdp);
      console.log('[CALL] Set remote offer and enabled controls');
      store.call.inCall = true;
      window.dispatchEvent(new Event('call:started'));
      return;
    }

    // Callee answers with SDP answer
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

    // Peer left
    if (msg.type === 'leave') {
      console.log('[CALL] Peer left the call');
      endCall('Peer left');
      return;
    }
  };
}
