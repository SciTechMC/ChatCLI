// api.js
const fetch = require('node-fetch');      // ← use v2 CJS
const BASE_URL = 'http://127.0.0.1:5123';

let sessionToken      = null;
let refreshTokenValue = null;

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (sessionToken) headers['Authorization'] = `Bearer ${sessionToken}`;

  // use the fetch you just required
  const res = await fetch(`${BASE_URL}${path}`, { method: 'POST', ...options, headers });

  if (res.status === 401 && refreshTokenValue) {
    const refreshed = await refreshToken();
    if (refreshed) {
      return request(path, options);
    } else {
      throw new Error('Session expired');
    }
  }

  if (!res.ok) {
    let data = {};
    try { data = await res.json(); } catch (_) {}
    throw new Error(data.message || res.statusText);
  }
  return res.json();
}

/* Convenience wrappers */
const verifyConnection = (body)              => request('/verify-connection', { body: JSON.stringify(body) });
const login            = ({ username, password })   => request('/user/login',    { body: JSON.stringify({ username, password }) });
const register         = ({ username, email, password }) => request('/user/register', { body: JSON.stringify({ username, email, password }) });
const verifyEmail      = ({ username, email_token }) =>
  request('/user/verify-email', { body: JSON.stringify({ username, email_token }) });
const fetchChats       = (username)          => request('/chat/fetch-chats',  { body: JSON.stringify({ username }) });
const fetchMessages    = (chatID, limit=100, order='ASC') => request('/chat/messages', { body: JSON.stringify({ chatID, limit, order }) });
const createChat       = (participants)      => request('/chat/create-chat',  { body: JSON.stringify({ participants }) });

async function refreshToken() {
  if (!refreshTokenValue) return false;
  const res = await fetch(`${BASE_URL}/user/refresh-token`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ refresh_token: refreshTokenValue }),
  });
  if (!res.ok) return false;
  const data = await res.json();
  sessionToken      = data.token;
  refreshTokenValue = data.refresh_token || refreshTokenValue;
  return true;
}

module.exports = {
  request,
  verifyConnection,
  login,
  register,
  verifyEmail,
  fetchChats,
  fetchMessages,
  createChat,
  refreshToken,
};
