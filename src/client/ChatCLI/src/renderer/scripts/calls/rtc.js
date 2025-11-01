import { store } from '../core/store.js';
import { getMic } from './media.js';
import { callSend } from './callSockets.js';

function ensureCallState() {
  store.call ??= {};
  store.call.queue ??= [];
  store.call.iceServers ??= [{ urls: 'stun:stun.l.google.com:19302' }];
}

export function createPC() {
  const pc = new RTCPeerConnection({ iceServers: store.call.iceServers });
  console.debug('[RTC] pc created', store.call.iceServers);

  // Add local mic (assumes getMic() already ran)
  store.call.localStream.getAudioTracks().forEach(track => {
    pc.addTrack(track, store.call.localStream);
  });

  pc.oniceconnectionstatechange = () => {
    console.log('[RTC] iceConnectionState:', pc.iceConnectionState);
  };
  pc.onconnectionstatechange = () => {
    console.log('[RTC] connectionState:', pc.connectionState);
    if (pc.connectionState === 'connected') window.dispatchEvent(new Event('call:connected'));
    if (['failed', 'disconnected', 'closed'].includes(pc.connectionState)) window.dispatchEvent(new Event('call:ended'));
  };
  pc.onsignalingstatechange = () => {
    console.log('[RTC] signalingState:', pc.signalingState);
  };

  pc.ontrack = (e) => {
    console.log('[RTC] remote track received; streams=', e.streams?.length || 0);
    if (store.refs.remoteAudio) {
      store.refs.remoteAudio.srcObject = e.streams[0];
      store.refs.remoteAudio.play?.().catch(err => console.warn('[RTC] remote play failed', err));
    }
  };

  pc.onicecandidate = (e) => {
    if (e.candidate) {
      callSend({ type: 'ice-candidate', chatID: store.currentChatID, candidate: e.candidate });
      console.log('[RTC] local ICE sent');
    } else {
      console.log('[RTC] ICE gathering complete');
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
    console.debug('[RTC] creating offer');
    const offer = await store.call.pc.createOffer({ offerToReceiveAudio: true });
    await store.call.pc.setLocalDescription(offer);
    console.debug('[RTC] local offer set; sending');
    callSend({ type: 'offer', chatID: store.currentChatID, sdp: offer });
  }
}

// Called when receiving an offer from remote
export async function setRemoteOffer(offerSDP) {
  if (!store.call.pc) {
    console.debug('[RTC] no pc on offer; init join flow');
    await getMic();
    createPC();
  }
  console.debug('[RTC] applying remote offer');
  await store.call.pc.setRemoteDescription(new RTCSessionDescription(offerSDP));
  const answer = await store.call.pc.createAnswer();
  await store.call.pc.setLocalDescription(answer);
  console.debug('[RTC] local answer set; sending');
  callSend({ type: 'answer', chatID: store.currentChatID, sdp: answer });
}

// Called when receiving an answer from remote
export async function setRemoteAnswer(answerSDP) {
  console.debug('[RTC] applying remote answer');
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

  window.dispatchEvent(new Event('call:ended'));
}

// Toggle mute state
export function toggleMute() {
  if (!store.call.localStream) return;
  store.call.isMuted = !store.call.isMuted;
  store.call.localStream.getAudioTracks().forEach(t => t.enabled = !store.call.isMuted);
  setStatus(store.call.isMuted ? 'Muted' : 'Unmuted');
  window.dispatchEvent(new CustomEvent('call:muted', { detail: { muted: store.call.isMuted } }));
}

// Called by "Start Call" button
export async function startCall() {
  store.call.inCall = true;
  await startAnswerFlow(true);
  window.dispatchEvent(new Event('call:started'));
}

// Called by "Join Call" button
export async function joinCall() {
  store.call.joiningArmed = true;
  await startAnswerFlow(false);

  if (store.call.pendingOffer) {
    await setRemoteOffer(store.call.pendingOffer);
    store.call.pendingOffer = null;
    store.call.inCall = true;
    window.dispatchEvent(new Event('call:started'));
  }
}