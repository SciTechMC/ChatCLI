const { app, BrowserWindow } = require('electron');

function createWindow() {
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      // nodeIntegration: true,    // ← not strictly required for `fetch`, but if you do plan to use any Node APIs in the renderer
      contextIsolation: false,    // ← allows you to use “window.fetch” (though fetch works by default)
    }
  });

  win.loadFile('startup.html');
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});