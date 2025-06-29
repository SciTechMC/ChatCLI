import {
  login,
  register,
  verifyEmail,
  verifyConnection,
  fetchChats,
  fetchMessages,
  refreshToken
} from './api.js';

let sessionToken = null;
let currentUser = null;
let ws = null;
let isOnline = null;
let retryTimer = null;

function updateStatus(online, message) {
  const statusMsg = document.getElementById('statusMsg');
  const retryBtn   = document.getElementById('retryBtn');
  const prevOnline = isOnline;
  isOnline = online;
  statusMsg.textContent = message;
  retryBtn.style.display = online ? 'none' : 'inline-block';
  if (online && prevOnline === false) alert('Reconnected to server!');
}

function checkConnection() {
  verifyConnection({ version: 'electron_app' })
    .then(() => {
      updateStatus(true, 'Online');
      const btnLogin = document.getElementById('btnLogin');
      const btnReg   = document.getElementById('btnRegister');
      if (btnLogin) btnLogin.disabled = false;
      if (btnReg)   btnReg.disabled   = false;
    })
    .catch(err => {
      console.error('Connection error:', err);
      updateStatus(false, 'Offline: ' + err.message);
      retryTimer = setTimeout(checkConnection, 10000);
    });
}

async function initAutoLogin() {
  const saved = await window.secureStore.loadSession();
  if (saved) {
    currentUser  = saved.username;
    // use refresh flow to obtain fresh access token
    try {
      const newToken = await refreshToken();
      sessionToken = newToken;
      initWebSocket();
      if (!location.pathname.endsWith('main.html')) {
        location.href = 'pages/main.html';
        return true;
      }
    } catch {
      await window.secureStore.clearSession(saved.username);
    }
  }
  return false;
}

document.addEventListener('DOMContentLoaded', async () => {
  // Auto-login attempt
  if (await initAutoLogin()) return;

  // Setup retry button
  const retryBtn = document.getElementById('retryBtn');
  if (retryBtn) retryBtn.onclick = () => {
    clearTimeout(retryTimer);
    updateStatus(null, 'Retrying...');
    checkConnection();
  };

  // Begin connection check
  checkConnection();

  const page = window.location.pathname.split('/').pop();

  if (page === 'login.html') {
    document.getElementById('loginForm').onsubmit = async e => {
      e.preventDefault();
      if (!isOnline) return alert('Cannot login: offline');
      const username = e.target.username.value;
      const password = e.target.password.value;
      try {
        const { token, refresh_token } = await login({ username, password });
        await window.secureStore.saveSession(username, refresh_token);
        sessionToken = token;
        currentUser  = username;
        initWebSocket();
        location.href = 'pages/main.html';
      } catch (err) {
        alert(err.message);
      }
    };
  }

  if (page === 'register.html') {
    document.getElementById('registerForm').onsubmit = async e => {
      e.preventDefault();
      if (!isOnline) return alert('Cannot register: offline');
      try {
        await register({
          username: e.target.regUsername.value,
          email: e.target.regEmail.value,
          password: e.target.regPassword.value
        });
        location.href = 'pages/verify.html';
      } catch (err) {
        alert(err.message);
      }
    };
  }

  if (page === 'verify.html') {
    document.getElementById('verifyForm').onsubmit = async e => {
      e.preventDefault();
      if (!isOnline) return alert('Cannot verify: offline');
      try {
        await verifyEmail({ token: e.target.token.value });
        location.href = 'pages/login.html';
      } catch (err) {
        alert(err.message);
      }
    };
  }

  if (page === 'main.html') {
    document.getElementById('btnSend').onclick = sendMessage;
    document.getElementById('btnLogout').onclick = async () => {
      await window.secureStore.clearSession(currentUser);
      location.href = 'pages/login.html';
    };
    loadChats();
  }
});

async function loadChats() {
  if (!isOnline) return;
  const chats = await fetchChats(currentUser, sessionToken);
  const list  = document.getElementById('chatList'); list.innerHTML = '';
  chats.forEach(chat => {
    const div = document.createElement('div');
    div.textContent = `Chat ${chat.chatID}: ${chat.participants.join(', ')}`;
    div.onclick = () => selectChat(chat.chatID);
    list.appendChild(div);
  });
}

function initWebSocket() {
  ws = new WebSocket('ws://localhost:5123/ws/chat');
  ws.onopen = () => ws.send(JSON.stringify({
    type: 'auth',
    username: currentUser,
    session_token: sessionToken
  }));
  ws.onmessage = ({ data }) => {
    const msg = JSON.parse(data);
    if (msg.type === 'message') displayIncoming(msg);
  };
}

async function selectChat(chatID) {
  if (!isOnline) return;
  const msgs = await fetchMessages(chatID, sessionToken);
  const win  = document.getElementById('messageWindow'); win.innerHTML = '';
  msgs.forEach(m => {
    const p = document.createElement('p'); p.textContent = `${m.sender}: ${m.text}`;
    win.appendChild(p);
  });
}

function sendMessage() {
  const text = document.getElementById('newMsg').value;
  if (!ws || ws.readyState !== WebSocket.OPEN) return alert('Cannot send: offline');
  ws.send(JSON.stringify({ type: 'message', chatID: null, text }));
  document.getElementById('newMsg').value = '';
}

function displayIncoming(msg) {
  // append to messageWindow if matching chat
  const p = document.createElement('p');
  p.textContent = `${msg.username}: ${msg.text}`;
  document.getElementById('messageWindow').appendChild(p);
}