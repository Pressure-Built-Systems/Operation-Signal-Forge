@echo off
title Signal Forge DApp Launcher
cd /d "%~dp0"

echo ========================================
echo   Signal Forge - Phase 1 DApp Launcher
echo ========================================
echo.

REM Start the AuthZ API (port 8787)
echo [1/2] Starting AuthZ API on http://127.0.0.1:8787 ...
start "SF-API" cmd /k "python dapp_api\app.py"

REM Give the API a moment to bind
timeout /t 2 /nobreak >nul

REM Start the static frontend (port 8080)
echo [2/2] Starting frontend on http://127.0.0.1:8080 ...
start "SF-Frontend" cmd /k "cd /d dapp && python -m http.server 8080"

REM Open the browser
timeout /t 1 /nobreak >nul
start http://127.0.0.1:8080/

echo.
echo Both servers are running in separate windows.
echo Close those windows to stop the DApp.
echo.
pause