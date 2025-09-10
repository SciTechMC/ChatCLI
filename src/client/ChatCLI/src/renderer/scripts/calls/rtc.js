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
  store.call.localStream.getAudioTracks().forEach(track => {
    pc.addTrack(track, store.call.localStream);
  });
  pc.ontrack = (e) => {
    if (store.refs.remoteAudio) store.refs.remoteAudio.srcObject = e.streams[0];
  };
  pc.onicecandidate = (e) => {
    if (e.candidate) callSend({ type: 'ice-candidate', chatID: store.currentChatID, candidate: e.candidate });
  };
  pc.onconnectionstatechange = () => {
    if (pc.connectionState === 'connected') setStatus('Connected ✅','ok');
    if (['failed','disconnected','closed'].includes(pc.connectionState)) setStatus('Call ended / issue','warn');
  };
  store.call.pc = pc;
  return pc;
}

// Called by "Start Call"
export async function startAnswerFlow(isCaller = false) {
  await getMic();
  createPC();

  if (isCaller) {
    const offer = await store.call.pc.createOffer({ offerToReceiveAudio: true });
    await store.call.pc.setLocalDescription(offer);
    callSend({ type: 'offer', chatID: store.currentChatID, sdp: offer });
    setStatus('Calling…');
  } else {
    // will answer once remote offer is set
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

  if (store.refs.btnLeave)    store.refs.btnLeave.disabled    = true;
  if (store.refs.btnJoinCall) store.refs.btnJoinCall.disabled = true;
  if (store.refs.btnMute)     store.refs.btnMute.disabled     = true;

  setStatus(reason);
}

export function toggleMute() {
  if (!store.call.localStream) return;
  store.call.isMuted = !store.call.isMuted;
  store.call.localStream.getAudioTracks().forEach(t => t.enabled = !store.call.isMuted);
  if (store.refs.btnMute) store.refs.btnMute.textContent = store.call.isMuted ? 'Unmute' : 'Mute';
  setStatus(store.call.isMuted ? 'Muted' : 'Unmuted');
}

export async function startCall() {
  ensureCallState();
  await ensureCallWSOpen();
  
  // Enable leave button immediately when starting a call
  store.call.inCall = true;
  store.refs?.btnLeave && (store.refs.btnLeave.disabled = false);
  
  callSend({ type: 'call-started', chatID: store.currentChatID });
  await startAnswerFlow(true);
}

export async function joinCall() {
  store.call.joiningArmed = true;
  await startAnswerFlow(false);
  if (store.call.pendingOffer) {
    await setRemoteOffer(store.call.pendingOffer);
    store.call.pendingOffer = null;
    store.call.inCall = true;
    if (store.refs.btnLeave) store.refs.btnLeave.disabled = false;
    if (store.refs.btnMute)  store.refs.btnMute.disabled  = false;
    setStatus('Joining…');
  } else {
    setStatus('Joining… (waiting for offer)');
  }
  if (store.refs.btnJoinCall) store.refs.btnJoinCall.disabled = true;
}
