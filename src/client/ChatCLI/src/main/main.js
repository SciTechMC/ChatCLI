// main.js
const { app, ipcMain, BrowserWindow } = require('electron')
const { saveRefreshToken, getRefreshToken, deleteRefreshToken } = require('../preload/authVault.js')
const path = require('path')
const keytar = require('keytar')
const { BASE_URL } = require('../preload/config.js');

const SERVICE = 'chatcli'

// --- REGISTER IPC HANDLERS FIRST (top-level) ---
ipcMain.handle('auth:storeRefresh', async (_e, { accountId, refreshToken }) => {
  await saveRefreshToken(accountId, refreshToken)
  return true
})

ipcMain.handle('auth:refresh', async (_e, { accountId }) => {
  const rt = await getRefreshToken(accountId)
  if (!rt) return { ok: false, reason: 'no_refresh' }
  const res = await fetch(`${BASE_URL}/user/refresh-token`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ refresh_token: rt }),
  })
  if (!res.ok) return { ok: false, reason: 'refresh_failed' }
  const { access_token, refresh_token: newRt } = await res.json()
  if (newRt && newRt !== rt) await saveRefreshToken(accountId, newRt)
  return { ok: true, access_token }
})

ipcMain.handle('auth:clear', async (_e, { accountId }) => {
  await deleteRefreshToken(accountId)
  return true
})

ipcMain.handle('secureStore:set', async (_evt, account, token) => {
  await keytar.setPassword(SERVICE, account, token)
  return true
})
ipcMain.handle('secureStore:get', async (_evt, account) => {
  return await keytar.getPassword(SERVICE, account)
})
ipcMain.handle('secureStore:delete', async (_evt, account) => {
  await keytar.deletePassword(SERVICE, account)
  return true
})
// -----------------------------------------------------------

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, '../preload/preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })
  win.loadFile(path.join(__dirname, '../renderer/pages', 'index.html'))
}

app.whenReady().then(createWindow)
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit() })
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })
