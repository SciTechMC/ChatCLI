import { store } from '../core/store.js';

let pc = null;
let ws = null;
let callingURL = null;
let hasSentOffer = false;

async function getMic() {
  const { initMedia } = await import('./media.js');

  if (!store.call.localStream || store.call.localStream.getAudioTracks().length === 0) {
    await initMedia();
    console.log('[RTC] getMic(): localStream tracks =', store.call.localStream?.getTracks());
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
    console.log('[RTC] createPeerConnection(): reusing existing PC');
    return pc;
  }

  console.log('[RTC] createPeerConnection(): creating new RTCPeerConnection with iceServers:', store.call.iceServers);

  pc = new RTCPeerConnection({ iceServers: store.call.iceServers });
  store.call.pc = pc;

  const localStream = await getMic();
  console.log('[RTC] Adding local tracks:', localStream.getTracks());
  for (const track of localStream.getTracks()) {
    console.log('[RTC] pc.addTrack:', track.kind, track.label);
    pc.addTrack(track, localStream);
  }

  pc.ontrack = (ev) => {
    console.log('[RTC] >>> ontrack fired! ev =', ev);

    const [remoteStream] = ev.streams;
    console.log('[RTC] remoteStream =', remoteStream);

    if (!remoteStream) {
      console.log('[RTC] ontrack fired BUT no remoteStream??');
      return;
    }

    store.call.remoteStream = remoteStream;
    const audioEl = store.refs.remoteAudio;

    if (audioEl) {
      console.log('[RTC] Setting audioEl.srcObject to remoteStream');
      audioEl.srcObject = remoteStream;

      audioEl.play().then(() => {
        console.log('[RTC] audioEl.play() SUCCESS');
      }).catch(err => {
        console.error('[RTC] audioEl.play() FAILED:', err);
      });
    } else {
      console.warn('[RTC] remoteAudio element is missing!');
    }

    window.dispatchEvent(new Event('call:connected'));
    console.log('[RTC] Remote media stream received');
  };

  pc.onicecandidate = (ev) => {
    console.log('[RTC] onicecandidate:', ev.candidate);
    if (!ev.candidate || !ws || ws.readyState !== WebSocket.OPEN) return;

    const msg = { type: 'candidate', payload: ev.candidate };
    try {
      ws.send(JSON.stringify(msg));
      console.log('[RTC] Sent ICE candidate');
    } catch (e) {
      console.error('[RTC] send candidate failed', e);
    }
  };

  pc.onconnectionstatechange = () => {
    console.log('[RTC] PC connection state =', pc.connectionState);
    if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
      endCall('connection_' + pc.connectionState);
    }
  };

  pc.oniceconnectionstatechange = () => {
    console.log('[RTC] ICE connection state =', pc.iceConnectionState);
  };

  ws.onclose = (ev) => {
    console.log('[RTC] Signaling WS CLOSED', ev.code, ev.reason);
  };

  window.dispatchEvent(new Event('call:started'));
  return pc;
}

async function ensureSignalingSocket(callId, isInitiator = false) {
  console.log('[RTC] ensureSignalingSocket(): callId =', callId, 'isInitiator =', isInitiator);

  try { ws?.close(); } catch {}
  ws = null;

  store.call.currentCallId = callId;
  const base = store.WS_URL || '';
  callingURL = base.replace(/\/ws$/, '') + '/call/' + encodeURIComponent(callId);
  console.log('[RTC] connecting to signalingWS:', callingURL);

  ws = new WebSocket(callingURL);
  store.call.callWS = ws;
  hasSentOffer = false;

  ws.onopen = () => {
    console.log('[RTC] Signaling WS OPEN:', callingURL);
    try {
      ws.send(JSON.stringify({ type: 'ready' }));
      console.log('[RTC] Sent READY handshake');
    } catch (e) {
      console.error('[RTC] Failed to send READY', e);
    }
  };

  ws.onmessage = async (event) => {
    console.log('[RTC] signaling WS message:', event.data);

    let data;
    try { data = JSON.parse(event.data); } catch { return; }

    const { type, payload } = data || {};
    if (!type) return;

    try {
      if (type === 'ready') {
        console.log('[RTC] Received READY handshake');

        if (isInitiator && !hasSentOffer) {
          try {
            const pcInstance = await createPeerConnection();
            console.log('[RTC] Creating OFFER (after READY)...');
            const offer = await pcInstance.createOffer();
            console.log('[RTC] OFFER created:', offer);

            await pcInstance.setLocalDescription(offer);
            console.log('[RTC] LocalDescription SET (offer)');

            ws.send(JSON.stringify({ type: 'offer', payload: offer }));
            console.log('[RTC] OFFER SENT to signaling WS');
            hasSentOffer = true;
          } catch (e) {
            console.error('[RTC] creating/sending offer failed', e);
          }
        }

      } else if (type === 'offer') {
        console.log('[RTC] Received OFFER:', payload);
        await handleOffer(payload);

      } else if (type === 'answer') {
        console.log('[RTC] Received ANSWER:', payload);
        await handleAnswer(payload);

      } else if (type === 'candidate') {
        console.log('[RTC] Received CANDIDATE:', payload);
        await handleCandidate(payload);

      } else if (type === 'call_ws_error') {
        console.error('[RTC] call_ws_error:', payload);
        endCall('ws_error');
      }
    } catch (e) {
      console.error('[RTC] error handling signaling msg', e);
    }
  };

  ws.onclose = () => {
    console.log('[RTC] Signaling WS CLOSED');
  };

  ws.onerror = (e) => {
    console.error('[RTC] Signaling WS ERROR', e);
  };
}

/** ---------- Signaling handlers ---------- */

async function handleOffer(offer) {
  console.log('[RTC] handleOffer(): applying remote offer');
  const pcInstance = await createPeerConnection();
  await pcInstance.setRemoteDescription(new RTCSessionDescription(offer));
  console.log('[RTC] RemoteDescription SET (offer)');

  const answer = await pcInstance.createAnswer();
  console.log('[RTC] ANSWER created:', answer);

  await pcInstance.setLocalDescription(answer);
  console.log('[RTC] LocalDescription SET (answer)');

  ws?.send(JSON.stringify({ type: 'answer', payload: answer }));
  console.log('[RTC] ANSWER SENT');

  console.log('[RTC] >>> CALL ESTABLISHED (handleOffer)');
}

async function handleAnswer(answer) {
  console.log('[RTC] handleAnswer(): applying remote answer');
  if (!pc) {
    console.error('[RTC] handleAnswer(): pc is null');
    return;
  }

  await pc.setRemoteDescription(new RTCSessionDescription(answer));
  console.log('[RTC] RemoteDescription SET (answer)');
  console.log('[RTC] >>> CALL ESTABLISHED (handleAnswer)');
}

async function handleCandidate(candidate) {
  console.log('[RTC] handleCandidate(): candidate =', candidate);

  if (!pc || !candidate) {
    console.warn('[RTC] No PC or no candidate');
    return;
  }

  try {
    await pc.addIceCandidate(new RTCIceCandidate(candidate));
    console.log('[RTC] ICE candidate added OK');
  } catch (e) {
    console.error('[RTC] Error adding ICE candidate', e);
  }
}

/** ---------- Public API ---------- */

export async function joinCall({ callId, isInitiator = false }) {
  console.log('[RTC] joinCall(): callId =', callId, 'isInitiator =', isInitiator);

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

  console.log('[RTC] toggleMute(): muted =', store.call.isMuted);

  for (const track of stream.getAudioTracks()) {
    console.log('[RTC] track', track.label, 'enabled =', !store.call.isMuted);
    track.enabled = !store.call.isMuted;
  }

  window.dispatchEvent(
    new CustomEvent('call:muted', { detail: { muted: store.call.isMuted } })
  );
}

export function endCall(reason = 'user') {
  console.log('[RTC] endCall(): reason =', reason);

  try {
    if (pc) {
      pc.getSenders().forEach((s) => {
        console.log('[RTC] stopping track:', s.track?.label);
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