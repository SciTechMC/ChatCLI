import { store } from '../core/store.js';

let pc = null;
let ws = null;
let callingURL = null;
let hasSentOffer = false;

async function getMic() {
  const { initMedia } = await import('./media.js');

  if (!store.call.localStream || store.call.localStream.getAudioTracks().length === 0) {
    await initMedia();
  }

  return store.call.localStream || new MediaStream();
}

async function clearPC() {
  if (pc) {
    try { pc.ontrack = null; } catch {}
    try { pc.onicecandidate = null; } catch {}
    try { pc.onconnectionstatechange = null; } catch {}
    try { pc.oniceconnectionstatechange = null; } catch {}
    try { pc.close(); } catch {}
  }
  pc = null;
  store.call.pc = null;
}

async function createPeerConnection() {
  if (pc) {
    return pc;
  }

  pc = new RTCPeerConnection({ iceServers: store.call.iceServers });
  store.call.pc = pc;

  const localStream = await getMic();
  for (const track of localStream.getTracks()) {
    pc.addTrack(track, localStream);
  }

  pc.ontrack = (ev) => {
    const [remoteStream] = ev.streams;

    if (!remoteStream) {
      return;
    }

    store.call.remoteStream = remoteStream;
    const audioEl = store.refs.remoteAudio;

    if (audioEl) {
      audioEl.srcObject = remoteStream;

    } else {
      console.warn('[RTC] remoteAudio element is missing!');
    }

    window.dispatchEvent(new Event('call:connected'));
  };

  pc.onicecandidate = (ev) => {
    if (!ev.candidate || !ws || ws.readyState !== WebSocket.OPEN) return;

    const msg = { type: 'candidate', payload: ev.candidate };
    try {
      ws.send(JSON.stringify(msg));
    } catch (e) {
      console.error('[RTC] send candidate failed', e);
    }
  };

  pc.onconnectionstatechange = () => {
    if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
      endCall('connection_' + pc.connectionState);
    }
  };

  window.dispatchEvent(new Event('call:started'));
  return pc;
}

async function ensureSignalingSocket(callId, isInitiator = false) {
  try { ws?.close(); } catch {}
  ws = null;

  store.call.currentCallId = callId;
  const base = store.WS_URL || '';
  callingURL = base.replace(/\/ws$/, '') + '/call/' + encodeURIComponent(callId);

  ws = new WebSocket(callingURL);
  store.call.callWS = ws;
  hasSentOffer = false;

  ws.onopen = () => {
    try {
      ws.send(JSON.stringify({ type: 'ready' }));
    } catch (e) {
      console.error('[RTC] Failed to send READY', e);
    }
  };

  ws.onmessage = async (event) => {
    let data;
    try { data = JSON.parse(event.data); } catch { return; }

    const { type, payload } = data || {};
    if (!type) return;

    try {
      if (type === 'ready') {
        if (isInitiator && !hasSentOffer) {
          try {
            const pcInstance = await createPeerConnection();
            const offer = await pcInstance.createOffer();
            await pcInstance.setLocalDescription(offer);

            ws.send(JSON.stringify({ type: 'offer', payload: offer }));
            hasSentOffer = true;
          } catch (e) {
            console.error('[RTC] creating/sending offer failed', e);
          }
        }

      } else if (type === 'offer') {
        await handleOffer(payload);

      } else if (type === 'answer') {
        await handleAnswer(payload);

      } else if (type === 'candidate') {
        await handleCandidate(payload);

      } else if (type === 'call_ws_error') {
        console.error('[RTC] call_ws_error:', payload);
        endCall('ws_error');
      }
    } catch (e) {
      console.error('[RTC] error handling signaling msg', e);
    }
  };

  ws.onerror = (e) => {
    console.error('[RTC] Signaling WS ERROR', e);
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
  if (!pc) {
    console.error('[RTC] handleAnswer(): pc is null');
    return;
  }

  await pc.setRemoteDescription(new RTCSessionDescription(answer));
}

async function handleCandidate(candidate) {
  if (!pc || !candidate) {
    console.warn('[RTC] No PC or no candidate');
    return;
  }

  try {
    await pc.addIceCandidate(new RTCIceCandidate(candidate));
  } catch (e) {
    console.error('[RTC] Error adding ICE candidate', e);
  }
}

/** ---------- Public API ---------- */

export async function joinCall({ callId, isInitiator = false }) {
  await clearPC();
  await ensureSignalingSocket(callId, isInitiator);
}

export async function toggleMute() {
  store.call.isMuted = !store.call.isMuted;

  const stream = store.call.localStream;
  if (!stream) {
    console.warn('[RTC] toggleMute(): no localStream');
    return;
  }

  for (const track of stream.getAudioTracks()) {
    track.enabled = !store.call.isMuted;
  }

  window.dispatchEvent(
    new CustomEvent('call:muted', { detail: { muted: store.call.isMuted } })
  );
}

export function endCall(reason = 'user') {
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
  hasSentOffer = false;

  window.dispatchEvent(new Event('call:ended'));
}