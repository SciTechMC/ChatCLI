// config.js
const HOST = '172.27.27.179';
const API_PORT = 5123;
const WS_PORT = 8765;

module.exports = {
  BASE_URL: `http://${HOST}:${API_PORT}`,
  WS_URL: `ws://${HOST}:${WS_PORT}/ws`,
};
