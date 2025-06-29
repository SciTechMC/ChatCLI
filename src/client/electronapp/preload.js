const { contextBridge, ipcRenderer } = require('electron');
const api = require('./api');

contextBridge.exposeInMainWorld('api', {
  login: api.login,
  register: api.register,
  verifyEmail: api.verifyEmail,
  verifyConnection: api.verifyConnection,
  fetchChats: api.fetchChats,
  fetchMessages: api.fetchMessages,
  createChat: api.createChat,
  refreshToken: api.refreshToken
});

contextBridge.exposeInMainWorld('secureStore', {
  saveSession: (username, refreshToken) => ipcRenderer.invoke('store-session', { username, refreshToken }),
  loadSession: () => ipcRenderer.invoke('get-session'),
  clearSession: username => ipcRenderer.invoke('clear-session', { username })
});