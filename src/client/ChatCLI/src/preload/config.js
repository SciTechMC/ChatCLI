const HOST = '127.0.0.1';
const API_PORT = 5123;
const WS_PORT = 8765;

module.exports = {
  BASE_URL: `http://${HOST}:${API_PORT}`,
  WS_URL: `ws://${HOST}:${WS_PORT}/ws`,
  CALL_URL: `ws://${HOST}:${WS_PORT}/call/`,
};