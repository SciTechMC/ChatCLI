// Shared front‑end logic
document.addEventListener('DOMContentLoaded', () => {
  try {
    const statusEl = document.getElementById('server-status');
    const retryBtn = document.getElementById('retry-btn');
    let online = false;
    const CHECK_INTERVAL = 10_000; // 10 s

    const loginBtn    = document.getElementById('login-btn');
    const registerBtn = document.getElementById('register-btn');

    loginBtn?.addEventListener('click', () => {
      window.location.href = 'login.html';
    });
    registerBtn?.addEventListener('click', () => {
      window.location.href = 'register.html';
    });

    async function checkServer() {
      if (statusEl) statusEl.textContent = 'Checking server…';
      try {
        console.log('calling verifyConnection…');
        const res = await window.api.verifyConnection({ version: 'electron_app' });
        console.log('verifyConnection →', res);

        // ——————————————— New logic ———————————————
        // If the API returns either a truthy `status === 'ok'` OR a non-empty `response`,
        // consider it a success. Otherwise treat `res.error` or fallback as failure.
        const ok = (res.status === 'ok') || Boolean(res.response);
        if (ok) {
          online = true;
          if (statusEl) statusEl.textContent = 'Server is online ✅';
          enableButtons();
        } else {
          // pick the first non-empty error-like field
          const message = res.message || res.error || 'Unknown error';
          throw new Error(message);
        }
        // ——————————————————————————————————————————————
      } catch (err) {
        console.error('checkServer error:', err);
        online = false;
        if (statusEl) statusEl.textContent = `Offline: ${err.message}`;
        disableButtons();
      }
    }

    function disableButtons() {
      document.querySelectorAll('[data-requires-online]')
        .forEach(btn => { btn.disabled = true; });
      window.dispatchEvent(new CustomEvent('online-status-changed', { detail: false }));
    }

    function enableButtons() {
      document.querySelectorAll('[data-requires-online]')
        .forEach(btn => { btn.disabled = false; });
      window.dispatchEvent(new CustomEvent('online-status-changed', { detail: true }));
    }

    retryBtn?.addEventListener('click', checkServer);

    /* ---------- Auto‑retry when offline ---------- */
    setInterval(() => { if (!online) checkServer(); }, CHECK_INTERVAL);

    /* Immediate check on load */
    checkServer();
  } catch (err) {
    console.error('renderer init error:', err);
  }
});
