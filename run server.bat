@echo off
REM Enable virtual environment
source .venv\Scripts\activate

REM Check for internet connection
echo Checking internet connection...
ping -n 1 google.com >nul 2>&1
if %errorlevel% neq 0 (
    echo No internet connection detected.
    echo Checking if dependencies are installed...
    python -m pip freeze | findstr python-dotenv >nul 2>&1
    if %errorlevel% neq 0 (
        echo Dependencies are not installed. Please connect to the internet and try again.
        pause
        exit /b
    ) else (
        echo All dependencies are installed.
    )
) else (
    echo Internet connection detected.
    echo Installing dependencies...
    python -m pip install -r requirements.txt
)

REM Check if python-dotenv is installed
python -m pip show python-dotenv >nul 2>&1
if %errorlevel% neq 0 (
    echo python-dotenv is not installed. Installing it now...
    python -m pip install python-dotenv
) else (
    echo python-dotenv is already installed.
)

REM Run the main script
python main.py
pause