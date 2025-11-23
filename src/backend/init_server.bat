@echo off
echo Installing dependencies…
pip install --upgrade -r requirements.txt

echo.
echo Running database initialization…
python install_update_server.py