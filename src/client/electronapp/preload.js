const { contextBridge } = require('electron');
const api = require('./api');

contextBridge.exposeInMainWorld('api', {
  login: api.login,
  register: api.register,
  verifyEmail: api.verifyEmail,
  fetchChats: api.fetchChats,
  createChat: api.createChat,
  fetchMessages: api.fetchMessages
});