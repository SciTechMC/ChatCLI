import { store } from '../core/store.js';

let pc = null;
let ws = null;
let callingURL = null;

async function getMic() {
  if (store.call.localStream) return store.call.localStream;
  const { initMedia } = await import('./media.js');
  await initMedia();
  return store.call.localStream;
}

async function createPeerConnection() {
  if (pc) return pc;

  pc = new RTCPeerConnection({ iceServers: store.call.iceServers });
  store.call.pc = pc;

  const localStream = await getMic();
  for (const track of localStream.getTracks()) {
    pc.addTrack(track, localStream);
  }

  pc.ontrack = (ev) => {
    const [remoteStream] = ev.streams;
    if (!remoteStream) return;
    store.call.remoteStream = remoteStream;
    const audioEl = store.refs.remoteAudio;
    if (audioEl) {
      audioEl.srcObject = remoteStream;
      audioEl.play().catch(() => {});
    }
    window.dispatchEvent(new Event('call:connected'));
  };

  pc.onicecandidate = (ev) => {
    if (!ev.candidate || !ws || ws.readyState !== WebSocket.OPEN) return;
    const msg = {
      type: 'candidate',
      payload: ev.candidate
    };
    try {
      ws.send(JSON.stringify(msg));
    } catch (e) {
      console.error('send candidate failed', e);
    }
  };

  pc.onconnectionstatechange = () => {
    const st = pc.connectionState;
    if (st === 'failed' || st === 'disconnected') {
      endCall('connection_' + st);
    }
  };

  window.dispatchEvent(new Event('call:started'));
  return pc;
}

async function ensureSignalingSocket(callId, isInitiator = false) {
  // reuse if already connected to this call
  if (ws && store.call.currentCallId === callId && ws.readyState === WebSocket.OPEN) {
    return;
  }

  // clean up any previous ws
  try { ws?.close(); } catch {}

  store.call.currentCallId = callId;
  const base = store.WS_URL || '';
  // store.WS_URL typically ends with /ws
  callingURL = base.replace(/\/ws$/, '') + '/call/' + encodeURIComponent(callId);
  ws = new WebSocket(callingURL);
  store.call.callWS = ws;

  ws.onopen = async () => {
    console.log('Call signaling WS open', callingURL);
    const pcInstance = await createPeerConnection();
    if (isInitiator) {
      try {
        const offer = await pcInstance.createOffer();
        await pcInstance.setLocalDescription(offer);
        ws.send(JSON.stringify({ type: 'offer', payload: offer }));
      } catch (e) {
        console.error('creating/sending offer failed', e);
      }
    }
  };

  ws.onmessage = async (event) => {
    let data;
    try { data = JSON.parse(event.data); } catch { return; }
    const { type, payload } = data || {};
    if (!type) return;
    try {
      if (type === 'offer') {
        await handleOffer(payload);
      } else if (type === 'answer') {
        await handleAnswer(payload);
      } else if (type === 'candidate') {
        await handleCandidate(payload);
      } else if (type === 'call_ws_error') {
        console.error('call ws error', payload || data);
        endCall('ws_error');
      }
    } catch (e) {
      console.error('error handling signaling msg', e);
    }
  };

  ws.onclose = () => {
    console.log('Call signaling WS closed');
  };

  ws.onerror = (e) => {
    console.error('Call signaling WS error', e);
  };
}

/** ---------- Signaling handlers ---------- */

async function handleOffer(offer) {
  const pcInstance = await createPeerConnection();
  await pcInstance.setRemoteDescription(new RTCSessionDescription(offer));
  const answer = await pcInstance.createAnswer();
  await pcInstance.setLocalDescription(answer);
  ws?.send(JSON.stringify({ type: 'answer', payload: answer }));
}

async function handleAnswer(answer) {
  if (!pc) return;
  await pc.setRemoteDescription(new RTCSessionDescription(answer));
}

async function handleCandidate(candidate) {
  if (!pc || !candidate) return;
  try {
    await pc.addIceCandidate(new RTCIceCandidate(candidate));
  } catch (e) {
    console.error('Error adding received ICE candidate', e);
  }
}

/** ---------- Public API ---------- */

export async function joinCall({ callId, isInitiator = false }) {
  await ensureSignalingSocket(callId, isInitiator);
}

export async function toggleMute() {
  store.call.isMuted = !store.call.isMuted;
  const stream = await getMic();
  for (const track of stream.getAudioTracks()) {
    track.enabled = !store.call.isMuted;
  }
  window.dispatchEvent(
    new CustomEvent('call:muted', { detail: { muted: store.call.isMuted } })
  );
}

export function endCall(reason = 'user') {
  console.log('Ending call:', reason);
  try {
    if (pc) {
      pc.getSenders().forEach((s) => {
        try { s.track?.stop(); } catch {}
      });
      pc.close();
    }
  } catch {}
  pc = null;

  try {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
  } catch {}
  ws = null;
  store.call.callWS = null;
  store.call.currentCallId = null;
  store.call.remoteStream = null;
  store.call.localStream = null;
  store.call.isMuted = false;
  store.call.pc = null;

  window.dispatchEvent(new Event('call:ended'));
}
