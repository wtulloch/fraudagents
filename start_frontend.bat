@echo off
cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo node_modules not found. Running npm install...
    npm install
)

echo Starting Fraud Detection Frontend...
npm run dev
pause
