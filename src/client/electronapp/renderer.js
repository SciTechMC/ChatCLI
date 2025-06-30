// Shared front-end logic
document.addEventListener('DOMContentLoaded', () => {
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
        const res = await window.api.login({
          username: document.getElementById('username').value.trim(),
          password: document.getElementById('password').value,
        });
        console.log('[login] response', res);
        await window.secureStore.set('refresh_token', res.refresh_token);
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
        const res = await window.api.register({
          username: document.getElementById('username').value.trim(),
          email:    document.getElementById('email').value.trim(),
          password: document.getElementById('password').value,
        });
        console.log('[register] response', res);
        location.href = 'verify.html';
      } catch (err) {
        console.error('[register] error', err);
      }
    });
  }

  /* — Verify Email page (CSP-safe) — */
  (() => {
    const verifyForm = document.getElementById('verify-form');
    if (!verifyForm) return;       // only run on verify.html

    // parse username from the URL: verify.html?username=alice
    const params   = new URLSearchParams(window.location.search);
    const username = params.get('username'); 

    const verifyBtn = document.getElementById('verify-submit');
    window.addEventListener('online-status-changed', ({ detail }) => {
      verifyBtn.disabled = !detail;
    });

    verifyForm.addEventListener('submit', async e => {
      e.preventDefault();
      const token = document.getElementById('token').value.trim();
      console.log('[verify] submitting', { username, token });

      try {
        const res = await window.api.verifyEmail({ username, token });
        console.log('[verify] response', res);
        location.href = 'login.html';
      } catch (err) {
        console.error('[verify] error', err);
        // you can display an inline error here if you like
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
