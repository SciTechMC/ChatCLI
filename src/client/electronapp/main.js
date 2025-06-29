const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('chatAPI', {
  fetchChats: data => ipcRenderer.invoke('chat-fetch', data),
  createChat: data => ipcRenderer.invoke('chat-create', data),
  sendMessage: data => ipcRenderer.invoke('chat-send', data),
  // ...
});