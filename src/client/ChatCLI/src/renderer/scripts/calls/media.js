import { store } from '../core/store.js';

// --- Media (microphone) ----------------------------------------------------

export async function initMedia() {
  let localStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: false,
      noiseSuppression: true,
      autoGainControl: true
    },
    video: false
  });
  store.call.localStream = localStream;
}

// --- Simple tone engine (ringback + ringtone) ------------------------------

// shared audio context
let _audioCtx = null;

function ensureCtx() {
  if (!_audioCtx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) {
      throw new Error('Web Audio API not supported');
    }
    _audioCtx = new AC();
  }
  return _audioCtx;
}

// resume audio context if suspended (required by some browsers)
export async function resumeAudioCtx() {
  try {
    const ctx = ensureCtx();
    if (ctx.state === 'suspended') {
      await ctx.resume();
    }
  } catch (e) {
    console.warn('resumeAudioCtx failed', e);
  }
}

// timers + osc handles
let _ringbackTimer, _ringbackOsc, _ringtoneTimer, _ringtoneOsc;

function stopOsc(osc) {
  try { osc.stop(); } catch {}
  try { osc.disconnect(); } catch {}
}

// --- Ringback (outgoing tone) ----------------------------------------------

export function playRingback() {
  stopRingback();
  const ctx = ensureCtx();
  // pattern: 400 Hz for 1s, 2s off
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
  if (_ringbackTimer) {
    clearInterval(_ringbackTimer);
    _ringbackTimer = null;
  }
  if (_ringbackOsc) {
    stopOsc(_ringbackOsc);
    _ringbackOsc = null;
  }
}

// --- Ringtone (incoming tone) ----------------------------------------------

export function playRingtone() {
  stopRingtone();
  const ctx = ensureCtx();

  const master = ctx.createGain();
  master.gain.value = 0.06;
  master.connect(ctx.destination);

  const sequence = [
    { f: 554.37, dur: 220 }, // C#5
    { rest: 90 },
    { f: 659.25, dur: 220 }, // E5
    { rest: 130 },
    { f: 783.99, dur: 260 }, // G5
  ];

  const ATTACK = 0.02;
  const RELEASE = 0.08;

  const scheduleAt = (startTime) => {
    let t = startTime;
    for (const step of sequence) {
      if (step.rest) {
        t += step.rest / 1000;
        continue;
      }
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.value = step.f;

      gain.gain.setValueAtTime(0, t);
      gain.gain.linearRampToValueAtTime(master.gain.value, t + ATTACK);
      gain.gain.setValueAtTime(master.gain.value, t + (step.dur / 1000) - RELEASE);
      gain.gain.linearRampToValueAtTime(0, t + (step.dur / 1000));

      osc.connect(gain).connect(master);
      osc.start(t);
      osc.stop(t + (step.dur / 1000) + 0.05);

      const lfo = ctx.createOscillator();
      const lfoGain = ctx.createGain();
      lfo.type = 'sine';
      lfo.frequency.value = 5.5;
      lfoGain.gain.value = 3;
      lfo.connect(lfoGain).connect(osc.frequency);
      lfo.start(t);
      lfo.stop(t + (step.dur / 1000));

      t += step.dur / 1000;
    }
    return t - startTime;
  };

  const start = ctx.currentTime + 0.02;
  const totalDur = scheduleAt(start);
  const loopMs = (totalDur * 1000) + 600;

  _ringtoneTimer = setInterval(() => {
    const t0 = ctx.currentTime + 0.02;
    scheduleAt(t0);
  }, loopMs);
}

export function stopRingtone() {
  if (_ringtoneTimer) {
    clearInterval(_ringtoneTimer);
    _ringtoneTimer = null;
  }
  if (_ringtoneOsc) {
    stopOsc(_ringtoneOsc);
    _ringtoneOsc = null;
  }
}