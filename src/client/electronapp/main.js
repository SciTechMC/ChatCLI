const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const keytar = require('keytar');

const SERVICE = 'MyChatApp';
let mainWindow;

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true
    }
  });
  mainWindow.loadFile(path.join(__dirname, 'pages', 'index.html'));
}

app.whenReady().then(createWindow);

// Secure session storage via keytar
ipcMain.handle('store-session', async (_, { username, refreshToken }) => {
  await keytar.setPassword(SERVICE, username, refreshToken);
});

ipcMain.handle('get-session', async () => {
  // For simplicity, assume a single saved account; in prod you’d track last user
  const accounts = await keytar.findCredentials(SERVICE);
  if (!accounts.length) return null;
  const { account: username, password: refreshToken } = accounts[0];
  return { username, refreshToken };
});

ipcMain.handle('clear-session', async (_, { username }) => {
  await keytar.deletePassword(SERVICE, username);
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});