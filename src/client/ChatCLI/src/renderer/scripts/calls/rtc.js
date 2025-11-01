import { store } from '../core/store.js';
import { getMic } from './media.js';
import { callSend, sendCallEndViaGlobal } from './callSockets.js';

let callToken = 0;

function ensureCallState() {
  store.call ??= {};
  store.call.queue ??= [];
  store.call.iceCandidateBuffer ??= [];
  store.call.iceServers ??= [
    { urls: 'stun:stun.l.google.com:19302' },
  ];
  store.call.forceRelay ??= false;

  // media + pc
  store.call.localStream ??= null;
  store.call.remoteStream ??= null;
  store.call.pc ??= null;

  // flags
  store.call.inCall ??= false;
  store.call.joiningArmed ??= false;
  store.call._offerInFlight ??= false;
  store.call._startedForCallId ??= null;
  store.call._lastOfferSDP ??= null;
  store.call.isMuted ??= false;
}

/** ---------- PeerConnection creation (binds to current callToken) ---------- */
function createPC() {
  ensureCallState();

  const pc = new RTCPeerConnection({
    iceServers: store.call.iceServers,
    iceTransportPolicy: store.call.forceRelay ? 'relay' : 'all',
  });

  pc._token = callToken;
  store.call.pc = pc;

  if (store.call.localStream) {
    for (const t of store.call.localStream.getAudioTracks()) {
      pc.addTrack(t, store.call.localStream);
    }
  }

  // --- event wiring ---
  pc.onicecandidate = (e) => {
    if (pc._token !== callToken) return;
    if (e.candidate) {
      callSend({ type: 'ice-candidate', chatID: store.currentChatID, candidate: e.candidate });
    }
  };

  pc.oniceconnectionstatechange = () => {
    if (pc._token !== callToken) return;
    console.log('[RTC] iceConnectionState:', pc.iceConnectionState);
  };

  pc.onconnectionstatechange = () => {
    if (pc._token !== callToken) return;
    console.log('[RTC] connectionState:', pc.connectionState);
    if (pc.connectionState === 'connected') {
      window.dispatchEvent(new Event('call:connected'));
    } else if (pc.connectionState === 'failed' || pc.connectionState === 'closed') {
      window.dispatchEvent(new Event('call:ended'));
    }
  };

  pc.onsignalingstatechange = () => {
    if (pc._token !== callToken) return;
    console.log('[RTC] signalingState:', pc.signalingState);
  };

  pc.ontrack = (e) => {
    if (pc._token !== callToken) return;
    if (!store.call.remoteStream) store.call.remoteStream = new MediaStream();
    store.call.remoteStream.addTrack(e.track);

    const el = store.refs?.remoteAudio;
    if (el) {
      if (el.srcObject !== store.call.remoteStream) el.srcObject = store.call.remoteStream;
      el.autoplay = true;
      el.playsInline = true;
      el.muted = false;
      el.play?.().catch((err) => {
        if (String(err?.name) !== 'AbortError') console.warn('[RTC] remote play failed', err);
      });
      e.track.onunmute = () => {
        try { if (el.srcObject !== store.call.remoteStream) el.srcObject = store.call.remoteStream; } catch {}
        el.play?.().catch(() => {});
      };
    }
  };

  return pc;
}

/** ---------- helpers ---------- */
function setMuted(muted) {
  ensureCallState();
  store.call.isMuted = !!muted;
  if (store.call.localStream) {
    for (const t of store.call.localStream.getAudioTracks()) t.enabled = !muted;
  }
  window.dispatchEvent(new CustomEvent('call:muted', { detail: { muted: store.call.isMuted } }));
}

async function primeRemoteAudio() {
  store.call.remoteStream = new MediaStream();
  const el = store.refs?.remoteAudio;
  if (el) {
    try { el.srcObject = store.call.remoteStream; } catch {}
    el.autoplay = true;
    el.playsInline = true;
    el.muted = false;
  }
}

/** ---------- public API ---------- */

// Button: Start Call (caller path)
export async function startCall() {
  ensureCallState();
  if (store.call.inCall) return;
  if (store.call.pc && store.call.pc.signalingState !== 'stable') return;
  if (store.call._offerInFlight) return;

  store.call._offerInFlight = true;
  try {
    store.call.inCall = true;

    // New call instance
    callToken += 1;
    store.call.iceCandidateBuffer = [];
    await primeRemoteAudio();
    await getMic();

    // create PC bound to this token
    const pc = createPC();

    // mute state applies immediately
    setMuted(store.call.isMuted);

    // create and send offer
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    callSend({ type: 'offer', chatID: store.currentChatID, sdp: offer });

    window.dispatchEvent(new Event('call:started'));
  } finally {
    store.call._offerInFlight = false;
  }
}

// Button: Join Call (callee path without SDP yet)
export async function joinCall() {
  ensureCallState();
  if (store.call.joiningArmed || store.call.inCall) return;

  store.call.joiningArmed = true;

  // New call instance or attaching to existing one
  callToken += 1;
  store.call.iceCandidateBuffer = [];
  await primeRemoteAudio();
  await getMic();
  createPC();

  setMuted(store.call.isMuted);
}

// Incoming offer from signaling
export async function setRemoteOffer(offerSDP) {
  ensureCallState();

  const serialized = JSON.stringify(offerSDP || {});
  if (store.call._lastOfferSDP === serialized) {
    console.debug('[RTC] duplicate offer ignored');
    return;
  }
  store.call._lastOfferSDP = serialized;

  if (!store.call.pc) {
    callToken += 1;
    store.call.iceCandidateBuffer = [];
    await primeRemoteAudio();
    await getMic();
    createPC();
    setMuted(store.call.isMuted);
  }

  const pc = store.call.pc;
  console.debug('[RTC] applying remote offer');
  await pc.setRemoteDescription(new RTCSessionDescription(offerSDP));

  // add any buffered ICE (arrived before remoteDescription)
  for (const cand of store.call.iceCandidateBuffer.splice(0)) {
    try { await pc.addIceCandidate(new RTCIceCandidate(cand)); } catch (e) { console.warn('[RTC] addIceCandidate (buffered) failed', e); }
  }

  const answer = await pc.createAnswer();
  await pc.setLocalDescription(answer);
  callSend({ type: 'answer', chatID: store.currentChatID, sdp: answer });

  store.call.inCall = true;
  window.dispatchEvent(new Event('call:started'));
}

// Incoming answer from signaling
export async function setRemoteAnswer(answerSDP) {
  ensureCallState();
  if (!store.call.pc) return;
  const pc = store.call.pc;

  console.debug('[RTC] applying remote answer');
  await pc.setRemoteDescription(new RTCSessionDescription(answerSDP));

  for (const cand of store.call.iceCandidateBuffer.splice(0)) {
    try { await pc.addIceCandidate(new RTCIceCandidate(cand)); } catch (e) { console.warn('[RTC] addIceCandidate (buffered) failed', e); }
  }
}

// Local UI: toggle mute
export function toggleMute() {
  setMuted(!store.call.isMuted);
}

// End the call from UI or remote signal
export function endCall(reason = 'Ended') {
  ensureCallState();

  // invalidate previous async handlers
  callToken += 1;

  // close pc
  try { store.call.pc?.close(); } catch {}
  store.call.pc = null;

  // remote audio
  const el = store.refs?.remoteAudio;
  if (el) {
    try { el.pause?.(); } catch {}
    try { el.srcObject = null; } catch {}
  }

  // stop streams
  try { store.call.remoteStream?.getTracks()?.forEach((t) => t.stop()); } catch {}
  store.call.remoteStream = null;

  try { store.call.localStream?.getTracks()?.forEach((t) => t.stop()); } catch {}
  store.call.localStream = null;

  // flush signaling
  store.call.iceCandidateBuffer = [];

  // try to notify both ways (global + per-call WS)
  if (store.call.inCall) {
    try { sendCallEndViaGlobal(store.currentChatID); } catch {}
    try { callSend({ type: 'leave', chatID: store.currentChatID, reason }); } catch {}
  }

  // reset flags
  store.call.inCall = false;
  store.call.joiningArmed = false;
  store.call._offerInFlight = false;
  store.call._startedForCallId = null;
  store.call._lastOfferSDP = null;
  store.call.isMuted = false;

  window.dispatchEvent(new Event('call:ended'));
}