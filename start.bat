@echo off
:: ModForge — One-click launcher
:: Starts the backend, AI server, and desktop app in separate windows.
:: Double-click this file to launch everything.

title ModForge Launcher
cd /d "%~dp0"

echo.
echo ============================================
echo   ModForge Launcher
echo ============================================
echo.

:: ── Check that setup has been run ───────────────────────────
if not exist "app\node_modules" (
    echo [!] Dependencies not installed. Running setup first...
    echo.
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup-dev.ps1"
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERROR] Setup failed. See messages above.
        pause
        exit /b 1
    )
    echo.
)

:: ── Start Backend (port 8420) ───────────────────────────────
echo [1/3] Starting backend on http://localhost:8420 ...
start "ModForge Backend" cmd /k "cd /d "%~dp0backend" && python -m uvicorn modforge.main:app --reload --port 8420"

:: Give the backend a moment to bind the port
timeout /t 3 /noq >nul

:: ── Start AI Server (port 8421) ─────────────────────────────
echo [2/3] Starting AI server on http://localhost:8421 ...
start "ModForge AI Server" cmd /k "cd /d "%~dp0ai" && python -m inference.server --port 8421"

timeout /t 2 /noq >nul

:: ── Start Desktop App ───────────────────────────────────────
echo [3/3] Starting desktop app...
start "ModForge App" cmd /k "cd /d "%~dp0app" && npm run tauri dev"

echo.
echo ============================================
echo   All services launched!
echo ============================================
echo.
echo   Backend:    http://localhost:8420/docs
echo   AI Server:  http://localhost:8421/docs
echo   App:        Tauri window should open shortly
echo.
echo   Close this window at any time — services
echo   run in their own windows.
echo.
pause
