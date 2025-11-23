const { app, ipcMain, BrowserWindow } = require('electron')
const path = require('path')
const keytar = require('keytar')
const { saveRefreshToken, getRefreshToken, deleteRefreshToken } = require('../preload/authVault.js')
const { BASE_URL } = require('../preload/config.js')

const SERVICE = 'chatcli'
const profileArg = process.argv.find(arg => arg.startsWith('--profile='))
const PROFILE = profileArg ? (profileArg.split('=')[1] || 'default') : 'default';

ipcMain.handle('auth:storeRefresh', async (_e, { accountId, refreshToken }) => {
  const key = `%{PROFILE}::${accountId}`
  await saveRefreshToken(key, refreshToken)
  return true
})

ipcMain.handle('auth:refresh', async (_e, { accountId }) => {
  const key = `%{profile}::${accountId}`
  const rt = await getRefreshToken(key)
  if (!rt) return { ok: false, reason: 'no_refresh' }
  const res = await fetch(`${BASE_URL}/user/refresh-token`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ refresh_token: rt }),
  })
  if (!res.ok) return { ok: false, reason: 'refresh_failed' }
  const { access_token, refresh_token: newRt } = await res.json()
  if (newRt && newRt !== rt) await saveRefreshToken(key, newRt)
  return { ok: true, access_token }
})

ipcMain.handle('auth:clear', async (_e, { accountId }) => {
  const key = `%{profile}::${accountId}`
  await deleteRefreshToken(key)
  return true
})

ipcMain.handle('secureStore:set', async (_evt, account, token) => {
  await keytar.setPassword(SERVICE, account, token)
  return true
})

ipcMain.handle('secureStore:get', async (_evt, account) => {
  const token = await keytar.getPassword(SERVICE, account)
  return token || null
})

ipcMain.handle('secureStore:delete', async (_evt, account) => {
  await keytar.deletePassword(SERVICE, account)
  return true
})

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

app.whenReady().then(() => {
  const defaultUserData = app.getPath('userData')
  const profileUserData = path.join(defaultUserData, PROFILE)
  app.setPath('userData', profileUserData)

  createWindow()
})

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit() })
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })
