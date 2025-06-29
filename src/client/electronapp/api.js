const BASE_URL = 'http://localhost:5123';
let sessionToken = null;
let inFlightRefresh = null;

async function request(path, options = {}, canRetry = true) {
  const headers = { ...options.headers };
  if (sessionToken) headers.Authorization = `Bearer ${sessionToken}`;

  const res = await fetch(BASE_URL + path, {
    method: options.method || 'GET',
    headers,
    body: options.body
  });

  if (res.status === 401 && canRetry) {
    // attempt token refresh once
    await doRefresh();
    return request(path, options, false);
  }
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// Login returns { token, refresh_token }
export function login({ username, password }) {
  return request('/user/login', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  });
}

export function register({ username, email, password }) {
  return request('/user/register', {
    method: 'POST',
    body: JSON.stringify({ username, email, password })
  });
}

export function verifyEmail({ token }) {
  return request('/user/verify-email', {
    method: 'POST',
    body: JSON.stringify({ token })
  });
}

export function verifyConnection({ version }) {
  return request('/verify-connection', {
    method: 'POST',
    body: JSON.stringify({ version })
  });
}

export function fetchChats(username, token) {
  sessionToken = token;
  return request('/chat/fetch-chats', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username })
  });
}

export function fetchMessages(chatID, token, limit = 50, order = 'ASC') {
  sessionToken = token;
  return request('/chat/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chatID, limit, order })
  });
}

export function createChat(participants, token) {
  sessionToken = token;
  return request('/chat/create-chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ participants })
  });
}

// Refresh access token using refresh endpoint and keychain
export async function refreshToken() {
  if (!inFlightRefresh) {
    inFlightRefresh = (async () => {
      const sess = await window.secureStore.loadSession();
      if (!sess) throw new Error('No session to refresh');
      const { refreshToken } = sess;
      const data = await fetch(BASE_URL + '/user/refresh-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
      if (!data.ok) throw new Error('Refresh failed');
      const { token: newToken, refresh_token: newRefresh } = await data.json();
      sessionToken = newToken;
      await window.secureStore.saveSession(sess.username, newRefresh);
      inFlightRefresh = null;
      return newToken;
    })();
  }
  return inFlightRefresh;
}