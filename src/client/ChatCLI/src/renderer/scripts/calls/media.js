import { store } from '../core/store.js';

export async function getMic() {
  if (store.call.localStream) return store.call.localStream;
  try {
    store.call.localStream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      video: false
    });
    store.call.localStream.getAudioTracks().forEach(t => t.enabled = !store.call.isMuted);
    return store.call.localStream;
  } catch (err) {
    console.error('[CALL] getMic error:', err);
    const { statusEl } = store.refs;
    if (statusEl) {
      statusEl.textContent = 'Microphone error';
      statusEl.className = 'status warn';
    }
    throw err;
  }
}
