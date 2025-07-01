// main.js
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const keytar = require('keytar');

app.disableHardwareAcceleration();                 // software rendering
app.commandLine.appendSwitch('disable-gpu');       // belt‐and‐braces

const SERVICE = 'chatcli';

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  // Load your UI directly from the pages folder
  win.loadFile(path.join(__dirname, 'pages', 'index.html'));
  console.log('[main] GPU off?', app.commandLine.hasSwitch('disable-gpu'));

  win.webContents.on('render-process-gone', (_e, details) => {
    console.error(
      '[main] renderer gone →',
      'reason:', details.reason,
      'exitCode:', details.exitCode
    );
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

/* ---------------- SecureStore IPC ---------------- */
ipcMain.handle('secureStore:set', async (_evt, account, token) => {
  await keytar.setPassword(SERVICE, account, token);
  return true;
});

ipcMain.handle('secureStore:get', async (_evt, account) => {
  return await keytar.getPassword(SERVICE, account);
});

ipcMain.handle('secureStore:delete', async (_evt, account) => {
  await keytar.deletePassword(SERVICE, account);
  return true;
});
