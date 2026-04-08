@echo off
:: ModForge — One-click setup
:: Downloads dependencies, installs everything, and prepares the project.
:: Double-click this file or run it from any terminal.

title ModForge Setup
cd /d "%~dp0"

echo.
echo ============================================
echo   ModForge Setup
echo ============================================
echo.

:: ── Bypass PowerShell execution policy and run setup ────────
echo Running setup script...
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup-dev.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Setup failed. See messages above.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Setup complete!
echo ============================================
echo.
echo You can now double-click  start.bat  to launch ModForge.
echo.
pause
