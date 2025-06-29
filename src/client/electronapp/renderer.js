// src/client/electronapp/renderer.js
const statusEl    = document.getElementById('status');
const retryBtn    = document.getElementById('btnRetry');
const loginBtn    = document.getElementById('btnLogin');
const registerBtn = document.getElementById('btnRegister');

const RETRY_INTERVAL = 10_000;
let retryTimer = null;

function setStatus(text, ok=false) {
  statusEl.innerText = text;
  statusEl.style.color = ok ? 'green' : 'red';
}
function disableButtons() {
  loginBtn.disabled = true;
  registerBtn.disabled = true;
}
function enableButtons() {
  loginBtn.disabled = false;
  registerBtn.disabled = false;
}

async function checkServer() {
  setStatus('Checking server…');
  disableButtons();
  try {
    const resp = await window.api.verifyConnection();
    console.log('[renderer] verifyConnection →', resp);
    setStatus('Server is online ✅', true);
    enableButtons();
  } catch (err) {
    console.error('[renderer] verifyConnection failed:', err);
    setStatus(`Offline: ${err.message}`);
    retryTimer = setTimeout(checkServer, RETRY_INTERVAL);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  checkServer();
  retryBtn.addEventListener('click', () => {
    clearTimeout(retryTimer);
    checkServer();
  });
});
