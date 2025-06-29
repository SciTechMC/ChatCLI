const BASE_URL = 'http://localhost:5123';

async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

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

export function fetchChats(username, token) {
  return request('/chat/fetch-chats', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ username })
  });
}

export function createChat(participants, token) {
  return request('/chat/create-chat', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ participants })
  });
}

export function fetchMessages(chatID, token, limit = 50, order = 'ASC') {
  return request('/chat/messages', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ chatID, limit, order })
  });
}