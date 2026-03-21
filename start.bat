@echo off
setlocal EnableDelayedExpansion

title Fraud Detection System — Startup

echo.
echo ============================================================
echo   Fraud Detection System — Starting All Services
echo ============================================================
echo.

:: ── Verify .env exists ────────────────────────────────────────────────────────
if not exist "%~dp0.env" (
    echo [ERROR] .env file not found! Copy .env.example to .env and fill in your Azure credentials.
    echo.
    pause
    exit /b 1
)

:: ── Start Backend (FastAPI + uvicorn) ─────────────────────────────────────────
echo [1/2] Starting Backend (FastAPI on http://localhost:8000) ...
echo       Logs: backend.log
echo.
start "Fraud Detection — Backend" /D "%~dp0" cmd /k ^
    "title Backend ^& .venv\Scripts\activate ^& uvicorn backend.main:app --reload --port 8000 --log-level info"

:: Wait a moment so backend has a head start before the browser opens
timeout /t 3 /nobreak >nul

:: ── Start Frontend (Vite dev server) ──────────────────────────────────────────
echo [2/2] Starting Frontend (Vite on http://localhost:5173) ...
echo.
start "Fraud Detection — Frontend" /D "%~dp0frontend" cmd /k ^
    "title Frontend ^& npm run dev"

:: Wait for Vite to start, then open browser
timeout /t 5 /nobreak >nul
start "" "http://localhost:5173"

echo.
echo ============================================================
echo   Services started in separate windows:
echo     Backend  →  http://localhost:8000
echo     Docs     →  http://localhost:8000/docs  (Swagger UI)
echo     Frontend →  http://localhost:5173
echo ============================================================
echo.
echo   Close the backend/frontend terminal windows to stop the services.
echo   This window can be closed.
echo.
