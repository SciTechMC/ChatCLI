const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const keytar = require('keytar');
const express = require('express');

app.disableHardwareAcceleration();
app.commandLine.appendSwitch('disable-gpu');

const SERVICE = 'my-chat-app';

// ── Step 2: Start Express ──
const staticServer = express()
  .use(express.static(path.join(__dirname, 'pages')))
  .listen(3000, () => {
    console.log('Static server running at http://localhost:3000');
  });

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    },
  });

  // ── Step 3: Load over HTTP ──
  win.loadURL('http://localhost:3000/index.html');
  console.log('[main] GPU off?', app.commandLine.hasSwitch('disable-gpu'));

  win.webContents.on('render-process-gone', (_e, details) => {
    console.error('[main] renderer gone → reason:', details.reason, 'exitCode:', details.exitCode);
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  // ── Step 4: Close Express server ──
  staticServer.close();
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
