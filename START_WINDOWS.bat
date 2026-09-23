@echo off
title B2B Outreach Framework
echo.
echo  Starting setup wizard...
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Python not found. Opening download page...
    start https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: Tick "Add Python to PATH" during install.
    echo  Then close this window and double-click START_WINDOWS.bat again.
    pause
    exit
)

:: Run wizard
python wizard.py
pause
