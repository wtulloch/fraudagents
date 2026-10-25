@echo off
cd /d "%~dp0"

where uv >nul 2>&1
if errorlevel 1 (
    echo ERROR: uv is not installed or not on PATH. See README.md for setup.
    pause
    exit /b 1
)

if not exist ".env" (
    echo ERROR: .env file not found. Copy .env.example to .env and configure it.
    pause
    exit /b 1
)

echo Starting Fraud Detection Backend...
uv run --locked python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
set "BACKEND_EXIT_CODE=%ERRORLEVEL%"
pause
exit /b %BACKEND_EXIT_CODE%
