@echo off
cd /d "%~dp0"

if not exist ".env" (
    echo ERROR: .env file not found. Copy .env.example to .env and configure it.
    pause
    exit /b 1
)

echo Starting Fraud Detection Backend...
call .venv\Scripts\activate.bat
.venv\Scripts\uvicorn.exe backend.main:app --reload --host 0.0.0.0 --port 8000
pause
