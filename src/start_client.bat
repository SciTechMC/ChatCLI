@echo off
cd clien
cd electronapp
cls
set ELECTRON_ENABLE_LOGGING=true
set ELECTRON_DISABLE_SECURITY_WARNINGS=true
rem Install dependencies (if you need to)
call npm install

rem Launch the app
call npm start

rem Wait for a keypress before closing
pause