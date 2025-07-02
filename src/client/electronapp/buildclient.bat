@echo off
set ELECTRON_ENABLE_LOGGING=true
set ELECTRON_DISABLE_SECURITY_WARNINGS=true
rem Install dependencies (if you need to)
call npm install

rem Package the app
call npm run package

rem Make the distributable
call npm run make

rem Wait for a keypress before closing
pause