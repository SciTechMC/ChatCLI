import { store } from '../core/store.js';
import { setRemoteOffer, setRemoteAnswer, endCall } from './rtc.js';

/** ---- small helpers ---- */
function ensureCallState() {
  store.call ??= {};
  store.call.queue ??= [];
  store.call.iceServers ??= [{ urls: 'stun:stun.l.google.com:19302' }];
}

function sendOnGlobalWS(payload) {
  if (!store.currentChatIsPrivate || !store.peerUsername) {
    showToast('Select a private chat to start a call', 'error'); return;
  }
  const ws = store.ws;
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.warn('[WS] global socket not open, cannot send', payload);
    return;
  }
  ws.send(JSON.stringify(payload));
}

/** Queue-or-send signaling messages (WebRTC-level) */
export function callSend(obj) {
  ensureCallState();
  const ws = store.call.callWS;
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

/** --- Call WS (per call_id) --- */
export function openCallWS(callId, username) {
  ensureCallState();
  if (store.call.currentCallId === callId &&
      store.call.callWS &&
      (store.call.callWS.readyState === WebSocket.OPEN ||
      store.call.callWS.readyState === WebSocket.CONNECTING)) {
    return;
  }
  // If a different call is in-flight, close it.
  if (store.call.callWS && store.call.currentCallId !== callId) {
    try { store.call.callWS.close(); } catch {}
  }
  store.call.currentCallId = callId;

  const base = new URL(store.WS_URL);
  base.pathname = base.pathname.replace(/\/?ws$/, '') + `/call/${encodeURIComponent(callId)}/${encodeURIComponent(username)}`;
  const callUrl = base.href;

  console.debug('[CALL-WS] opening', callUrl);
  const ws = new WebSocket(callUrl);
  store.call.callWS = ws;

  ws.onopen = () => {
    console.log('[CALL-WS] open');
    flushQueue();
  };

  ws.onclose = (e) => {
    console.warn('[CALL-WS] close', e.code, e.reason);
    store.call.callWS = null;
  };

  ws.onerror = (e) => {
    console.error('[CALL-WS] error', e);
  };

  ws.onmessage = async (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch (err) {
      console.error('[CALL-WS] parse error', err, ev.data);
      return;
    }
    console.debug('[CALL-WS] msg', msg);

    // SDP/ICE only on this socket
    if (msg.type === 'offer') {
      console.debug('[CALL] recv offer; joiningArmed=', !!store.call.joiningArmed);
      const s = msg.sdp?.sdp || JSON.stringify(msg.sdp);
      if (store.call._lastOfferSDP === s) {
        console.debug('[CALL] duplicate offer ignored');
        return;
      }
      store.call._lastOfferSDP = s;

      if (!store.call.joiningArmed) {
        store.call.pendingOffer = msg.sdp;
        window.dispatchEvent(new CustomEvent('call:incoming', {
          detail: { chatID: msg.chatID, from: msg.from, call_id: msg.call_id }
        }));
        return;
      }
      await setRemoteOffer(msg.sdp);
      store.call.inCall = true;
      window.dispatchEvent(new Event('call:started'));
      return;
    }

    if (msg.type === 'answer') {
      console.debug('[CALL] recv answer; signalingState=', store.call.pc?.signalingState);
      if (store.call.pc && store.call.pc.signalingState === 'have-local-offer') {
        await setRemoteAnswer(msg.sdp);
        window.dispatchEvent(new Event('call:answer'));
      }
      return;
    }

    if (msg.type === 'ice-candidate' && msg.candidate) {
      const c = msg.candidate.candidate || '';
      if (/\b\.local\b/i.test(c) || /\b::1\b/i.test(c) || /\bfe80:/i.test(c) ||
          /\b0\.0\.0\.0\b/.test(c) || /\b169\.254\./.test(c) || /\b127\.0\.0\.1\b/.test(c)) {
        console.debug('[CALL] dropped unsuitable ICE candidate:', c);
        return;
      }
      if (!store.call.pc || !store.call.pc.remoteDescription) {
        store.call.iceCandidateBuffer.push(msg.candidate);
        console.debug('[CALL] remote ICE buffered (pc not ready)');
        return;
      }
      try {
        await store.call.pc.addIceCandidate(new RTCIceCandidate(msg.candidate));
        console.debug('[CALL] remote ICE added');
      } catch (e) {
        console.error('[CALL] ICE add failed:', e);
      }
      return;
    }

    if (msg.type === 'leave') {
      console.log('[CALL] peer left');
      endCall('Peer left');
      return;
    }
  };
}

/** --- Send call control via GLOBAL WS --- */
export function sendCallInviteViaGlobal({ chatID, callee }) {
  sendOnGlobalWS({ type: 'call_invite', chatID, callee });
}
export function sendCallAcceptViaGlobal(chatID) {
  sendOnGlobalWS({ type: 'call_accept', chatID });
}
export function sendCallDeclineViaGlobal(chatID) {
  sendOnGlobalWS({ type: 'call_decline', chatID });
}
export function sendCallEndViaGlobal(chatID) {
  sendOnGlobalWS({ type: 'call_end', chatID });
}