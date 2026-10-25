@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

title Fraud Detection — Azure Provisioning

echo.
echo ============================================================
echo   Fraud Detection System — Azure Resource Provisioning
echo   (Run this ONCE before using start.bat for the first time)
echo ============================================================
echo.

if not exist "%~dp0.env" (
    echo [ERROR] .env not found. Copy .env.example to .env and fill in Azure credentials first.
    pause
    exit /b 1
)

where uv >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv is not installed or not on PATH. See README.md for setup.
    pause
    exit /b 1
)

echo [1/3] Creating Azure AI Search indexes...
uv run --locked python -m scripts.create_search_indexes
if errorlevel 1 ( echo [FAILED] Search index creation failed. Check your AZURE_SEARCH_* vars. & pause & exit /b 1 )
echo.

echo [2/3] Registering Foundry agents via MAF...
uv run --locked python -m scripts.setup_foundry_agents
if errorlevel 1 ( echo [FAILED] Foundry agent setup failed. Check your AZURE_AI_FOUNDRY_* vars. & pause & exit /b 1 )
echo.

echo [3/3] Generating and indexing synthetic test data (500 records, 15%% fraud)...
uv run --locked python -m scripts.generate_synthetic_data --records 500 --fraud-rate 0.15 --seed 42
if errorlevel 1 ( echo [FAILED] Synthetic data generation failed. & pause & exit /b 1 )
echo.

echo ============================================================
echo   Provisioning complete! You can now run start.bat
echo ============================================================
echo.
pause
