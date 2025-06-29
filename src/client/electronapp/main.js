// src/client/electronapp/main.js
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const keytar = require('keytar');

const SERVICE = 'ChatCLI-Electron';
let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  mainWindow.loadFile(path.join(__dirname, 'pages', 'index.html'));
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// — Secure session storage via Keytar —

// Save the refresh token under the given username
ipcMain.handle('store-session', async (_, { username, token }) => {
  await keytar.setPassword(SERVICE, username, token);
});

// Load a saved session: return { username, token } or null
ipcMain.handle('get-session', async () => {
  const creds = await keytar.findCredentials(SERVICE);
  if (creds.length === 0) return null;
  const { account: username, password: token } = creds[0];
  return { username, token };
});

// Clear a session for the given username
ipcMain.handle('clear-session', async (_, { username }) => {
  await keytar.deletePassword(SERVICE, username);
});
