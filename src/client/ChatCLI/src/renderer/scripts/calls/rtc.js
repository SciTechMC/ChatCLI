import { store } from '../core/store.js';

/** ---------- PeerConnection creation ---------- */
async function createPC() {
  const pc = new RTCPeerConnection({ iceServers: store.call.iceServers });
  store.call.pc = pc;
  if (store.call.localStream) {
    localStream.getTracks().forEach(t => pc.addTrack(t, localStream));
  }
  return pc;
}

async function makeOffer() {
  let pc = pc;
    pc.ontrack = e => (remoteAudioElement.scrObject = e.streams[0]);
    pc.onicecandidate = e => e.candidate && console.log('ICE:', e.candidate.candidate);

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    await new Promise(res => {
        if (pc.iceGatheringState === 'complete') return res();
        pc.ongatheringstatechange = () =>
            pc.iceGatheringState === 'complete' && res();
    });

    sdpBoxElement.value = JSON.stringify(peerConnection.localDescription);
}

async function applyAnswer() {
    const answer = JSON.parse(sdpBoxElement.value);
    await peerConnection.setRemoteDescription(answer);
    console.log('Caller: remote answer applied');
}

/** ---------- helpers ---------- */
async function setMuted(muted) {
  store.call.isMuted = !!muted;
  if (store.call.localStream) {
    for (const t of store.call.localStream.getAudioTracks()) t.enabled = !muted;
  }
  window.dispatchEvent(new CustomEvent('call:muted', { detail: { muted: store.call.isMuted } }));
}