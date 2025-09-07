// main.js
const { app, ipcMain, BrowserWindow } = require('electron')
const { saveRefreshToken, getRefreshToken, deleteRefreshToken } = require('./authVault')
const path = require('path')
const keytar = require('keytar')
// If Node < 18, uncomment next line for fetch:
// const fetch = (...a) => import('node-fetch').then(({default:f}) => f(...a))

app.disableHardwareAcceleration()
app.commandLine.appendSwitch('disable-gpu')

const SERVICE = 'chatcli'

// --- REGISTER IPC HANDLERS FIRST (top-level) ---
ipcMain.handle('auth:storeRefresh', async (_e, { accountId, refreshToken }) => {
  await saveRefreshToken(accountId, refreshToken)
  return true
})

ipcMain.handle('auth:refresh', async (_e, { accountId }) => {
  const rt = await getRefreshToken(accountId)
  if (!rt) return { ok: false, reason: 'no_refresh' }
  const res = await fetch('http://109.88.13.230:5123/user/refresh-token', {
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

console.log('[main] IPC registered: auth:* and secureStore:*')
// -----------------------------------------------------------

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
  })
  win.loadFile(path.join(__dirname, 'pages', 'index.html'))
  console.log('[main] GPU off?', app.commandLine.hasSwitch('disable-gpu'))
}

app.whenReady().then(createWindow)
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit() })
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })
