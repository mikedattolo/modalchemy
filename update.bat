@echo off
:: ModForge — One-click updater
:: Pulls latest changes and refreshes dependencies/tools.

title ModForge Update
cd /d "%~dp0"

echo.
echo ============================================
echo   ModForge Update
echo ============================================
echo.

if not exist "app\package.json" (
    echo [ERROR] Cannot find app\package.json.
    echo         Make sure this file is in the root of the modalchemy repo.
    echo.
    pause
    exit /b 1
)

echo Running update script...
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\update-dev.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================
    echo   Update failed — see messages above
    echo ============================================
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Update complete!
echo ============================================
echo.
echo You can now run start.bat
pause
