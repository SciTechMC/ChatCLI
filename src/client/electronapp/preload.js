//  G:\ChatCLI\src\client\electronapp\preload.js

// OPTIONAL: keep these two lines for sanity logs
console.log('[preload] starting, __dirname =', __dirname);

const { contextBridge, ipcRenderer } = require('electron');
const api = require('./pages/api.js');               // stays CommonJS

/* -------- Expose REST API wrapper -------- */
contextBridge.exposeInMainWorld('api', {
  request:          api.request,
  verifyConnection: api.verifyConnection,
  login:            api.login,
  register:         api.register,
  verifyEmail:      api.verifyEmail,
  fetchChats:       api.fetchChats,
  fetchMessages:    api.fetchMessages,
  createChat:       api.createChat,
  refreshToken:     api.refreshToken,
  getSessionToken:    () => sessionToken,
  setSessionToken:    (tok) => { sessionToken = tok; },
  setRefreshToken:    (tok) => { refreshTokenValue = tok; },
  initializeTokens:   api.initializeTokens, // Add this
});

/* -------- Expose secureStore via keytar -------- */
contextBridge.exposeInMainWorld('secureStore', {
  set:    (account, token) => ipcRenderer.invoke('secureStore:set', account, token),
  get:    (account)        => ipcRenderer.invoke('secureStore:get', account),
  delete: (account)        => ipcRenderer.invoke('secureStore:delete', account),
});

console.log('[preload] expose complete');

const WebSocket = require('ws');

contextBridge.exposeInMainWorld('chatAPI', {
  connect: (token) => {
    const ws = new WebSocket('ws://localhost:8765/ws');
    ws.on('open', () => ws.send(JSON.stringify({ type: 'auth', token })));
    ws.on('message', (data) => {
      // re-emit into the DOM so your renderer code can listen
      window.dispatchEvent(new CustomEvent('ws-message', {
        detail: JSON.parse(data)
      }));
    });
    return ws;
  }
});