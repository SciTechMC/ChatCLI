@echo off
set ELECTRON_ENABLE_LOGGING=true
set ELECTRON_DISABLE_SECURITY_WARNINGS=true
rem Install dependencies (if you need to)
call npm install
call npx electron-builder install-app-deps --platform=win32 --arch=x64
rem Launch the app
call npm start

rem Wait for a keypress before closing
pause