import { store } from '../core/store.js';
import { getMic } from './media.js';
import { callSend, setStatus, ensureCallWSOpen } from './callSockets.js';

function ensureCallState() {
  store.call ??= {};
  store.call.queue ??= [];
  store.call.iceServers ??= [{ urls: 'stun:stun.l.google.com:19302' }];
}

export function createPC() {
  const pc = new RTCPeerConnection({ iceServers: store.call.iceServers });

  // Add local mic
  store.call.localStream.getAudioTracks().forEach(track => {
    pc.addTrack(track, store.call.localStream);
  });

  // Remote audio
  pc.ontrack = (e) => {
    if (store.refs.remoteAudio) store.refs.remoteAudio.srcObject = e.streams[0];
  };

  // Trickle ICE
  pc.onicecandidate = (e) => {
    if (e.candidate) callSend({ type: 'ice-candidate', chatID: store.currentChatID, candidate: e.candidate });
  };

  // Connection lifecycle
  pc.onconnectionstatechange = () => {
    if (pc.connectionState === 'connected') setStatus('Connected ✅', 'ok');
    if (['failed', 'disconnected', 'closed'].includes(pc.connectionState)) {
      setStatus('Call ended / issue', 'warn');
      // Let UI know if we drop unexpectedly
      window.dispatchEvent(new Event('call:ended'));
    }
  };

  store.call.pc = pc;
  return pc;
}

// Called by "Start Call" or "Join"
export async function startAnswerFlow(isCaller = false) {
  await getMic();
  createPC();

  if (isCaller) {
    const offer = await store.call.pc.createOffer({ offerToReceiveAudio: true });
    await store.call.pc.setLocalDescription(offer);
    callSend({ type: 'offer', chatID: store.currentChatID, sdp: offer });
    setStatus('Calling…');
  } else {
    // callee waits for remote offer; see setRemoteOffer
  }
}

export async function setRemoteOffer(offerSDP) {
  if (!store.call.pc) { await getMic(); createPC(); }
  await store.call.pc.setRemoteDescription(new RTCSessionDescription(offerSDP));
  const answer = await store.call.pc.createAnswer();
  await store.call.pc.setLocalDescription(answer);
  callSend({ type: 'answer', chatID: store.currentChatID, sdp: answer });
  setStatus('Answer sent');
}

export async function setRemoteAnswer(answerSDP) {
  await store.call.pc.setRemoteDescription(new RTCSessionDescription(answerSDP));
}

export function endCall(reason = 'Ended') {
  try { if (store.call.pc) store.call.pc.close(); } catch {}
  store.call.pc = null;

  if (store.call.localStream) {
    store.call.localStream.getTracks().forEach(t => t.stop());
    store.call.localStream = null;
  }
  if (store.call.inCall) callSend({ type: 'leave', chatID: store.currentChatID, reason });

  store.call.inCall = false;
  store.call.joiningArmed = false;
  store.call.pendingOffer = null;
  store.call.isMuted = false;

  // No more direct DOM toggling here; UI listens to events:
  setStatus(reason);
  window.dispatchEvent(new Event('call:ended'));
}

export function toggleMute() {
  if (!store.call.localStream) return;
  store.call.isMuted = !store.call.isMuted;
  store.call.localStream.getAudioTracks().forEach(t => t.enabled = !store.call.isMuted);
  setStatus(store.call.isMuted ? 'Muted' : 'Unmuted');
  window.dispatchEvent(new CustomEvent('call:muted', { detail: { muted: store.call.isMuted } }));
}

export async function startCall() {
  ensureCallState();
  await ensureCallWSOpen();

  // Flip to in-call immediately from the caller side
  store.call.inCall = true;

  callSend({ type: 'call-started', chatID: store.currentChatID });
  await startAnswerFlow(true);
  window.dispatchEvent(new Event('call:started'));
}

export async function joinCall() {
  store.call.joiningArmed = true;
  await startAnswerFlow(false);

  if (store.call.pendingOffer) {
    await setRemoteOffer(store.call.pendingOffer);
    store.call.pendingOffer = null;
    store.call.inCall = true;
    setStatus('Joining…');
    window.dispatchEvent(new Event('call:started'));
  } else {
    setStatus('Joining… (waiting for offer)');
    // when the offer arrives, callSockets will set inCall and dispatch 'call:started'
  }
}
