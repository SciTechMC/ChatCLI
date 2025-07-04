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

  function setServerStatus(online, msg) {
    const statusEl = document.getElementById('server-status');
    if (!statusEl) return;
    statusEl.classList.toggle('status-online',  online);
    statusEl.classList.toggle('status-offline', !online);
    statusEl.querySelector('.status-text').textContent = msg;
  }

  async function checkServer() {
    setServerStatus(false, 'Checking server…');
    try {
      const res = await window.api.verifyConnection({ version: 'electron_app' });
      const ok = (res.status === 'ok') || Boolean(res.response);
      if (ok) {
        online = true;
        setServerStatus(true, 'Server is online');
        enableButtons();
      } else {
        throw new Error(res.message || res.error || 'Unknown error');
      }
    } catch (err) {
      online = false;
      setServerStatus(false, `Offline: ${err.message}`);
      disableButtons();
    }
  }

  retryBtn?.addEventListener('click', checkServer);
  setInterval(() => { if (!online) checkServer(); }, CHECK_INTERVAL);
  checkServer();

  /* — Startup page navigation — */
  const loginBtn    = document.getElementById('login-btn');
  const registerBtn = document.getElementById('register-btn');

  loginBtn?.addEventListener('click', () => {
    window.location.href = 'login.html';
  });
  registerBtn?.addEventListener('click', () => {
    window.location.href = 'register.html';
  });

  /* — Login page — */
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    const loginBtn = document.getElementById('login-submit');
    window.addEventListener('online-status-changed', ({ detail }) => {
      loginBtn.disabled = !detail;
    });

    loginForm.addEventListener('submit', async e => {
      e.preventDefault();
      clearMessages(loginForm);
      showStatus(loginForm, 'Logging in…');
      loginBtn.disabled = true;
      try {
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        const res = await window.api.login({ username, password });
        await window.secureStore.set('session_token', res.access_token);
        await window.secureStore.set('refresh_token', res.refresh_token);
        await window.secureStore.set('username', username);
        window.api.setRefreshToken(res.refresh_token);
        showStatus(loginForm, 'Login successful! Redirecting…', 'info');
        setTimeout(() => location.href = 'main.html', 1000);
      } catch (err) {
        showError(loginForm, `Login failed: ${err.message || 'Unknown error'}`);
      } finally {
        loginBtn.disabled = false;
        loginBtn.textContent = 'Log In';
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
      clearMessages(registerForm);
      showStatus(registerForm, 'Registering…');
      try {
        const username = document.getElementById('username').value.trim();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const res = await window.api.register({ username, email, password });
        showStatus(registerForm, 'Registration successful! Redirecting to verification…', 'info');
        setTimeout(() => {
          location.href = `verify.html?username=${encodeURIComponent(username)}`;
        }, 1200);
      } catch (err) {
        showError(registerForm, `Registration failed: ${err.message || 'Unknown error'}`);
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
      clearMessages(verifyForm);
      showStatus(verifyForm, 'Verifying email…');
      const email_token = document.getElementById('token').value.trim();
      try {
        const res = await window.api.verifyEmail({ username, email_token });
        showStatus(verifyForm, 'Email verified! Redirecting to login…', 'info');
        setTimeout(() => location.href = 'login.html', 1200);
      } catch (err) {
        showError(verifyForm, `Verification failed: ${err.message || 'Server error'}`);
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
      clearMessages(resetForm);
      showStatus(resetForm, 'Requesting password reset…');
      try {
        const username = document.getElementById('username').value.trim();
        const email = document.getElementById('email').value.trim();
        const res = await window.api.request(
          '/user/reset-password-request',
          { body: JSON.stringify({ username, email }) }
        );
        showStatus(resetForm, 'Reset link sent! Redirecting…', 'info');
        setTimeout(() => location.href = 'index.html', 1200);
      } catch (err) {
        showError(resetForm, `Reset failed: ${err.message || 'Unknown error'}`);
      }
    });
  }
});

/* Helper functions for form messages */
function showStatus(form, message, type = 'info') {
  let statusEl = form.querySelector('#status-container');
  if (!statusEl) {
    statusEl = document.createElement('div');
    statusEl.id = 'status-container';
    form.insertBefore(statusEl, form.firstChild);
  }
  statusEl.textContent = message;
  statusEl.className = type === 'error' ? 'error-message' : 'info-message';
}

function showError(form, message) {
  let errorEl = form.querySelector('#error-container');
  if (!errorEl) {
    errorEl = document.createElement('div');
    errorEl.id = 'error-container';
    form.insertBefore(errorEl, form.firstChild);
  }
  errorEl.textContent = message;
  errorEl.className = 'error-message';
}

function clearMessages(form) {
  const statusEl = form.querySelector('#status-container');
  if (statusEl) statusEl.textContent = '';
  const errorEl = form.querySelector('#error-container');
  if (errorEl) errorEl.textContent = '';
}
