let toastContainer;

/** Ensure a host container in the corner */
function ensureContainer() {
  if (toastContainer) return toastContainer;
  toastContainer = document.createElement('div');
  toastContainer.id = 'toast-container';
  Object.assign(toastContainer.style, {
    position: 'fixed',
    top: '20px',
    right: '20px',
    zIndex: '1000',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    pointerEvents: 'none' // container doesn't block clicks
  });
  document.body.appendChild(toastContainer);
  return toastContainer;
}

/**
 * Show a popup toast with a message.
 * @param {string} message
 * @param {'info'|'warning'|'error'} [type='info']
 * @param {number} [duration=3000]  // how long to show (ms)
 */
export function showToast(message, type = 'info', duration = 3000) {
  const container = ensureContainer();

  // root
  const toast = document.createElement('div');
  toast.classList.add('toast', type);
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  toast.style.setProperty('--life', `${Math.max(1200, duration)}ms`);

  // icon
  const icon = document.createElement('div');
  icon.className = 'toast-icon';
  icon.innerHTML =
    type === 'error'   ? '⛔' :
    type === 'warning' ? '⚠️' :
                          'ℹ️';

  // message
  const msg = document.createElement('div');
  msg.className = 'toast-message';
  msg.textContent = message;

  // close
  const close = document.createElement('button');
  close.className = 'toast-close';
  close.setAttribute('aria-label', 'Dismiss');
  close.innerHTML = '✕';

  toast.append(icon, msg, close);
  container.appendChild(toast);

  // life / pause / resume logic
  let endAt = Date.now() + duration;
  let timerId = setTimeout(dismiss, duration);

  function pause() {
    if (!timerId) return;
    clearTimeout(timerId);
    timerId = null;
    toast.classList.add('paused');
  }
  function resume() {
    if (timerId) return;
    const remaining = Math.max(0, endAt - Date.now());
    toast.classList.remove('paused');
    timerId = setTimeout(dismiss, remaining);
  }
  function dismiss() {
    toast.style.animation = 'toast-exit .22s ease forwards';
    // allow exit animation to play before removal
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
  }

  // interactions
  close.addEventListener('click', () => {
    if (timerId) clearTimeout(timerId);
    dismiss();
  });

  // hover pauses the timer + progress bar
  toast.addEventListener('mouseenter', () => {
    const remaining = Math.max(0, endAt - Date.now());
    endAt = Date.now() + remaining; // freeze countdown
    pause();
  });
  toast.addEventListener('mouseleave', () => {
    // recompute end time and restart timer
    const remaining = Math.max(0, endAt - Date.now());
    endAt = Date.now() + remaining;
    resume();
  });

  return toast;
}