// renderer.js
document.addEventListener('DOMContentLoaded', async () => {
  /* — Server-check setup — */
  const statusEl = document.getElementById('server-status');
  const retryBtn = document.getElementById('retry-btn');
  let online = false;
  const CHECK_INTERVAL = 10_000; // 10 seconds

  function disableButtons() {
    document.querySelectorAll('[data-requires-online]')
      .forEach(btn => btn.disabled = true);
    window.dispatchEvent(new CustomEvent('online-status-changed', { detail: false }));
  }

  function enableButtons() {
    document.querySelectorAll('[data-requires-online]')
      .forEach(btn => btn.disabled = false);
    window.dispatchEvent(new CustomEvent('online-status-changed', { detail: true }));
  }

  async function checkServer() {
    if (statusEl) statusEl.textContent = 'Checking server…';
    try {
      console.log('calling verifyConnection…');
      const res = await window.api.verifyConnection({ version: 'electron_app' });
      console.log('verifyConnection →', res);
      const ok = (res.status === 'ok') || Boolean(res.response);
      if (ok) {
        online = true;
        statusEl.textContent = 'Server is online ✅';
        enableButtons();
      } else {
        throw new Error(res.message || res.error || 'Unknown error');
      }
    } catch (err) {
      console.error('checkServer error:', err);
      online = false;
      statusEl.textContent = `Offline: ${err.message}`;
      disableButtons();
    }
  }

  retryBtn?.addEventListener('click', checkServer);
  setInterval(() => { if (!online) checkServer(); }, CHECK_INTERVAL);
  checkServer();

  /* — Startup page navigation — */
  document.getElementById('login-btn')
    ?.addEventListener('click', () => location.href = 'login.html');
  document.getElementById('register-btn')
    ?.addEventListener('click', () => location.href = 'register.html');

  /* — Login page — */
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    const loginBtn = document.getElementById('login-submit');
    window.addEventListener('online-status-changed', ({ detail }) => {
      loginBtn.disabled = !detail;
    });

    loginForm.addEventListener('submit', async e => {
      e.preventDefault();
      console.log('[login] submitting');
      try {
        // Grab what the user typed
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;

        // Call the API
        const res = await window.api.login({ username, password });
        console.log('[login] response', res);

        // ── STORE TOKENS ──
        // Store the access_token (for WS auth) as session_token:
        await window.secureStore.set('session_token', res.access_token);
        // Also keep the refresh_token for HTTP-layer calls:
        await window.secureStore.set('refresh_token', res.refresh_token);
        await window.secureStore.set('username', username);

        // Tell the HTTP-API layer about the new refresh token
        window.api.setRefreshToken(res.refresh_token);

        // Go to the main chat
        location.href = 'main.html';
      } catch (err) {
        console.error('[login] error', err);
      }
    });
  }

  /* — Register page — */
  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    const registerBtn = document.getElementById('register-submit');
    window.addEventListener('online-status-changed', ({ detail }) => {
      registerBtn.disabled = !detail;
    });

    registerForm.addEventListener('submit', async e => {
      e.preventDefault();
      console.log('[register] submitting');

      try {
        const username = document.getElementById('username').value.trim();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const res = await window.api.register({ username, email, password });
        console.log('[register] response', res);
        location.href = `verify.html?username=${encodeURIComponent(username)}`;
      } catch (err) {
        console.error('[register] error', err);
        const errorEl = document.getElementById('error-message') || document.createElement('div');
        errorEl.id = 'error-message';
        errorEl.textContent = `Registration failed: ${err.message || 'Unknown error'}`;
        errorEl.className = 'error';
        if (!document.getElementById('error-message')) {
          registerForm.insertBefore(errorEl, registerForm.firstChild);
        }
      }
    });
  }

  /* — Verify Email page — */
  (() => {
    const verifyForm = document.getElementById('verify-form');
    if (!verifyForm) return;

    const params = new URLSearchParams(window.location.search);
    const username = params.get('username');
    if (username) {
      const userInfo = document.createElement('p');
      userInfo.textContent = `Verifying account for: ${username}`;
      userInfo.className = 'user-info';
      verifyForm.insertBefore(userInfo, verifyForm.firstChild);
    }

    verifyForm.addEventListener('submit', async e => {
      e.preventDefault();
      const email_token = document.getElementById('token').value.trim();
      try {
        const res = await window.api.verifyEmail({ username, email_token });
        console.log('[verify] Success:', res);
        alert('Email verified successfully! Redirecting to login...');
        location.href = 'login.html';
      } catch (err) {
        console.error('[verify] error', err);
        const errorEl = document.getElementById('error-message') || document.createElement('div');
        errorEl.id = 'error-message';
        errorEl.textContent = `Verification failed: ${err.message || 'Server error'}`;
        errorEl.className = 'error';
        if (!document.getElementById('error-message')) {
          verifyForm.insertBefore(errorEl, verifyForm.firstChild);
        }
      }
    });
  })();

  /* — Reset Password page — */
  const resetForm = document.getElementById('reset-request-form');
  if (resetForm) {
    const resetBtn = document.getElementById('reset-submit');
    window.addEventListener('online-status-changed', ({ detail }) => {
      resetBtn.disabled = !detail;
    });
    resetForm.addEventListener('submit', async e => {
      e.preventDefault();
      console.log('[reset] submitting');
      try {
        const email = document.getElementById('email').value.trim();
        const res = await window.api.request(
          '/user/reset-password-request',
          { body: JSON.stringify({ email }) }
        );
        console.log('[reset] response', res);
        location.href = 'index.html';
      } catch (err) {
        console.error('[reset] error', err);
      }
    });
  }
});
