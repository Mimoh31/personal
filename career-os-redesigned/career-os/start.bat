@echo off
cd /d "%~dp0"

echo Checking for dependencies...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies, one-time only...
    pip install -r requirements.txt
)

echo Starting Career OS...
start "" http://127.0.0.1:5000
python app.py
