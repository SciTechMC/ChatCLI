const API_HOST = 'chat.puam.be';
const WS_HOST = 'ws.chat.puam.be';
const API_PORT = 5123;
const WS_PORT = 8765;

module.exports = {
  BASE_URL: `http://${API_HOST}:${API_PORT}`,
  WS_URL: `ws://${WS_HOST}:${WS_PORT}/ws`,
  CALL_URL: `ws://${WS_HOST}:${WS_PORT}/call/`,
};