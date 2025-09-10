// renderer.js
document.addEventListener('DOMContentLoaded', async () => {
  const statusEl = document.getElementById('server-status');
  const retryBtn = document.getElementById('retry-btn');
  let online = false;
  const CHECK_INTERVAL = 10_000;

  // access token: memory only
  let accessToken = null;
  function setAccess(token) {
    accessToken = token;
    if (window.api && typeof window.api.setAccessToken === 'function') {
      window.api.setAccessToken(token);
    }
  }
  function clearAccess() {
    setAccess(null);
  }

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

    const spinner = statusEl.querySelector('.spinner');
    if (spinner) spinner.style.display = online ? 'none' : 'inline-block';

    statusEl.classList.toggle('status-online', online);
    statusEl.classList.toggle('status-offline', !online);
    statusEl.querySelector('.status-text').textContent = msg;
  }

  // run ONLY after server is online so we don't block UI
  async function tryAutoLoginIfNeeded() {
    if (accessToken) return;
    if (!window.secureStore) return;
    const accountId = await window.secureStore.get('username');
    if (!accountId) return;
    if (!window.auth || typeof window.auth.refresh !== 'function') return;

    try {
      const res = await window.auth.refresh(accountId); // expected { ok, access_token }
      if (res && res.ok && res.access_token) {
        setAccess(res.access_token);
        setTimeout(() => { location.href = 'main.html'; }, 200);
      }
    } catch {
      // ignore; user will see login UI as usual
    }
  }

  async function checkServer() {
    setServerStatus(false, 'Checking server…');
    try {
      const data = await window.api.verifyConnection({ version: 'electron_app' });
      const ok = (typeof data === 'string') || (data && (data.response || data.message));
      if (ok) {
        online = true;
        setServerStatus(true, 'Server is online');
        enableButtons();
        // now that we're online, try silent refresh (non-blocking)
        tryAutoLoginIfNeeded();
      } else {
        const errMsg = data && (data.message || data.error) || 'Unknown error';
        throw new Error(errMsg);
      }
    } catch (err) {
      online = false;
      setServerStatus(false, `Offline: ${err.message}`);
      disableButtons();
    }
  }

  retryBtn?.addEventListener('click', checkServer);
  setInterval(() => { if (!online) checkServer(); }, CHECK_INTERVAL);
  checkServer(); // unchanged: first check happens immediately

  const loginBtn    = document.getElementById('login-btn');
  const registerBtn = document.getElementById('register-btn');
  loginBtn?.addEventListener('click', () => location.href = 'login.html');
  registerBtn?.addEventListener('click', () => location.href = 'register.html');

  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    const loginBtn = document.getElementById('login-submit');
    window.addEventListener('online-status-changed', ({ detail }) => {
      loginBtn.disabled = !detail;
    });

    loginForm.addEventListener('submit', async e => {
      e.preventDefault();
      loginBtn.disabled = true;
      loginBtn.textContent = 'Logging in…';

      try {
        const username = loginForm.username.value.trim();
        const password = loginForm.password.value;
        const res = await window.api.login({ username, password });

        // keep access in memory only
        setAccess(res.access_token);

        // store refresh in OS keychain via main; persist only the username
        if (window.auth && typeof window.auth.storeRefresh === 'function') {
          await window.auth.storeRefresh(username, res.refresh_token);
        }
        if (window.secureStore && typeof window.secureStore.set === 'function') {
          await window.secureStore.set('username', username);
        }

        showToast('Login successful! Redirecting…', 'info');
        setTimeout(() => location.href = 'main.html', 1000);
      } catch (err) {
        showToast('Login failed: ' + (err.message || 'Unknown error'), 'error');
        loginBtn.disabled = false;
        loginBtn.textContent = 'Log In';
      }
    });
  }

  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    const registerBtn = document.getElementById('register-submit');
    window.addEventListener('online-status-changed', ({ detail }) => {
      registerBtn.disabled = !detail;
    });

    registerForm.addEventListener('submit', async e => {
      e.preventDefault();
      registerBtn.disabled = true;
      registerBtn.textContent = 'Registering…';
    
      try {
        const username = registerForm.username.value.trim();
        const email = registerForm.email.value.trim();
        const password = registerForm.password.value;
    
        await window.api.register({ username, email, password });
    
        showToast('Account created! Redirecting to verification…', 'info');
        setTimeout(() => {
          location.href = `verify.html?username=${encodeURIComponent(username)}`;
        }, 1000);
      } catch (err) {
        showToast('Registration failed: ' + (err.message || 'Unknown error'), 'error');
        registerBtn.disabled = false;
        registerBtn.textContent = 'Register';
      }
    });
  }

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
      const btn = verifyForm.querySelector('button');
      btn.disabled = true;
      btn.textContent = 'Verifying…';

      const email_token = document.getElementById('token').value.trim();
      try {
        await window.api.verifyEmail({ username, email_token });
        showToast('Email verified! Redirecting to login…', 'info');
        setTimeout(() => location.href = 'login.html', 1200);
      } catch (err) {
        showToast('Verification failed: ' + (err.message || 'Server error'), 'error');
        btn.disabled = false;
        btn.textContent = 'Verify';
      }
    });
  })();

  const resetForm = document.getElementById('reset-password-form');
  if (resetForm) {
    const resetBtn = document.getElementById('reset-password-submit');
    window.addEventListener('online-status-changed', ({ detail }) => {
      resetBtn.disabled = !detail;
    });

    resetForm.addEventListener('submit', async e => {
      e.preventDefault();
      resetBtn.disabled = true;
      resetBtn.textContent = 'Sending…';

      try {
        const username = resetForm.username.value.trim();
        await window.api.request('/user/reset-password-request', {
          body: JSON.stringify({ username })
        });
        showToast('If the username exists, a reset link has been sent. Please check your inbox.', 'info');
      } catch (err) {
        showToast('Reset failed: ' + (err.message || 'Unknown error'), 'error');
        resetBtn.disabled = false;
        resetBtn.textContent = 'Send reset email';
      }
    });
  }
});

/* Toast-only messaging (no status divs) */
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'fadeOut 0.3s ease-in';
    toast.addEventListener('animationend', () => toast.remove());
  }, 3000);
}