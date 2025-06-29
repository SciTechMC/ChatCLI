// src/client/electronapp/api.js
const BASE_URL = 'http://localhost:5123';
let sessionToken = null;
let inFlightRefresh = null;

async function request(path, options = {}, canRetry = true) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (sessionToken) headers.Authorization = `Bearer ${sessionToken}`;

  let res;
  try {
    console.debug(`[api] ${options.method||'GET'} ${BASE_URL+path}`, options.body);
    res = await fetch(BASE_URL + path, {
      method: options.method || 'GET',
      headers,
      body: options.body
    });
  } catch (err) {
    console.error('[api] network error', err);
    throw err;
  }

  if (res.status === 401 && canRetry) {
    console.warn('[api] 401 → refreshing token');
    await refreshToken();
    return request(path, options, false);
  }
  if (!res.ok) {
    const txt = await res.text().catch(()=>'');
    throw new Error(`HTTP ${res.status}: ${txt}`);
  }
  return res.json();
}

async function login({ username, password }) {
  const data = await request('/user/login', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  });
  // data = { token: accessToken, refresh_token }
  sessionToken = data.token;
  await window.secureStore.saveSession(username, data.refresh_token);
  return data;
}

async function register({ username, email, password }) {
  return request('/user/register', {
    method: 'POST',
    body: JSON.stringify({ username, email, password })
  });
}

async function verifyEmail({ token }) {
  return request('/user/verify-email', {
    method: 'POST',
    body: JSON.stringify({ token })
  });
}

async function verifyConnection(version = 'electron_app') {
  return request('/verify-connection', {
    method: 'POST',
    body: JSON.stringify({ version })
  });
}

async function fetchChats(username) {
  return request('/chat/fetch-chats', {
    method: 'POST',
    body: JSON.stringify({ username })
  });
}

async function fetchMessages(chatID, limit = 50, order = 'ASC') {
  return request('/chat/messages', {
    method: 'POST',
    body: JSON.stringify({ chatID, limit, order })
  });
}

async function createChat(participants) {
  return request('/chat/create-chat', {
    method: 'POST',
    body: JSON.stringify({ participants })
  });
}

async function refreshToken() {
  if (!inFlightRefresh) {
    inFlightRefresh = (async () => {
      const sess = await window.secureStore.loadSession();
      if (!sess || !sess.username || !sess.token) {
        inFlightRefresh = null;
        throw new Error('No refresh token stored');
      }
      const { username, token: storedRefresh } = sess;

      const res = await fetch(BASE_URL + '/user/refresh-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: storedRefresh })
      });
      if (!res.ok) {
        await window.secureStore.clearSession(username);
        inFlightRefresh = null;
        throw new Error(`Refresh failed ${res.status}`);
      }
      const { token: newAccess, refresh_token: newRefresh } = await res.json();
      sessionToken = newAccess;
      await window.secureStore.saveSession(username, newRefresh);
      inFlightRefresh = null;
      return newAccess;
    })();
  }
  return inFlightRefresh;
}

module.exports = {
  login,
  register,
  verifyEmail,
  verifyConnection,
  fetchChats,
  fetchMessages,
  createChat,
  refreshToken
};
