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

// --- Simple tone engine (ringback + ringtone) ---
let _audioCtx, _ringbackTimer, _ringbackOsc, _ringtoneTimer, _ringtoneOsc;

function ensureCtx() {
  _audioCtx = _audioCtx || new (window.AudioContext || window.webkitAudioContext)();
  return _audioCtx;
}

function stopOsc(osc) {
  try { osc.stop(); } catch {}
  try { osc.disconnect(); } catch {}
}

export function playRingback() {
  stopRingback();
  const ctx = ensureCtx();
  // pattern: 400 Hz for 1s, 2s off (very simple EU-ish ringback feel)
  const on = 1000, off = 2000;
  const tick = () => {
    _ringbackOsc = ctx.createOscillator();
    const gain = ctx.createGain();
    gain.gain.value = 0.05;
    _ringbackOsc.frequency.value = 400;
    _ringbackOsc.connect(gain).connect(ctx.destination);
    _ringbackOsc.start();
    setTimeout(() => stopOsc(_ringbackOsc), on);
  };
  tick();
  _ringbackTimer = setInterval(tick, on + off);
}

export function stopRingback() {
  if (_ringbackTimer) { clearInterval(_ringbackTimer); _ringbackTimer = null; }
  if (_ringbackOsc) { stopOsc(_ringbackOsc); _ringbackOsc = null; }
}

export function playRingtone() {
  stopRingtone();
  const ctx = ensureCtx();
  // pattern: beep-beep (800Hz 200ms, pause 100ms, 800Hz 200ms), rest 1s
  const onDur = 200, shortGap = 100, rest = 1000;
  const tick = () => {
    const burst = (freq, startMs, dur) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      gain.gain.value = 0.07;
      osc.frequency.value = freq;
      osc.connect(gain).connect(ctx.destination);
      const t0 = ctx.currentTime + startMs / 1000;
      osc.start(t0);
      osc.stop(t0 + dur / 1000);
    };
    burst(800, 0, onDur);
    burst(800, onDur + shortGap, onDur);
  };
  tick();
  _ringtoneTimer = setInterval(tick, onDur + shortGap + onDur + rest);
}

export function stopRingtone() {
  if (_ringtoneTimer) { clearInterval(_ringtoneTimer); _ringtoneTimer = null; }
  if (_ringtoneOsc) { stopOsc(_ringtoneOsc); _ringtoneOsc = null; }
}
