// src/client/electronapp/preload.js
const path = require('path');
const { contextBridge, ipcRenderer } = require('electron');

// Require your api wrapper by absolute path
const api = require(path.join(__dirname, 'api.js'));

contextBridge.exposeInMainWorld('api', {
  login:            api.login,
  register:         api.register,
  verifyEmail:      api.verifyEmail,
  verifyConnection: api.verifyConnection,
  fetchChats:       api.fetchChats,
  fetchMessages:    api.fetchMessages,
  createChat:       api.createChat
});

contextBridge.exposeInMainWorld('secureStore', {
  saveSession: (username, token) =>
    ipcRenderer.invoke('store-session', { username, token }),
  loadSession: () =>
    ipcRenderer.invoke('get-session'),
  clearSession: username =>
    ipcRenderer.invoke('clear-session', { username })
});
