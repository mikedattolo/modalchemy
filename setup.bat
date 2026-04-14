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

:: ── Verify we're in the right directory ─────────────────────
if not exist "app\package.json" (
    echo [ERROR] Cannot find app\package.json.
    echo         Make sure this file is in the root of the modalchemy repo.
    echo.
    pause
    exit /b 1
)

:: ── Bypass PowerShell execution policy and run setup ────────
echo Running setup script...
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup-dev.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================
    echo   Setup failed — see messages above
    echo ============================================
    echo.
    echo Common fixes:
    echo   - Install Visual Studio Build Tools with "Desktop development with C++"
    echo     https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo   - Install Node.js 20 LTS from https://nodejs.org
    echo   - Install Python 3.10+ from https://python.org
    echo   - Install Rust from https://rustup.rs
    echo   - Install Java 8+ from https://adoptium.net
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
