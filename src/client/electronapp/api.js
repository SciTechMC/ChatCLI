const API_BASE = "http://localhost:5123";

window.API_URLS = {
  VERIFY_CONNECTION: `${API_BASE}/verify-connection`,
  USER_LOGIN: `${API_BASE}/user/login`,
  USER_REGISTER: `${API_BASE}/user/register`,
  USER_RESET_PASSWORD_REQUEST: `${API_BASE}/user/reset-password-request`,
  USER_VERIFY_EMAIL: `${API_BASE}/user/verify-email`,
  USER_RESET_PASSWORD: `${API_BASE}/user/reset-password`,
  CHAT_INDEX: `${API_BASE}/chat/`,
  CHAT_FETCH_CHATS: `${API_BASE}/chat/fetch-chats`,
  CHAT_CREATE_CHAT: `${API_BASE}/chat/create-chat`,
  CHAT_MESSAGES: `${API_BASE}/chat/messages`,
  // add more as needed
};
