@echo off
REM DPA Image Toolkit Launcher
REM Place this file in your Scripts folder or app folder
REM Double-click to launch the application

setlocal enabledelayedexpansion

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

REM Change to the script directory
cd /d "%SCRIPT_DIR%"

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ================================================================
    echo ERROR: Python is not installed or not in your PATH
    echo ================================================================
    echo.
    echo To fix this:
    echo   1. Install Python from https://www.python.org/downloads/
    echo   2. Make sure to check "Add Python to PATH" during installation
    echo   3. Restart your computer
    echo.
    pause
    exit /b 1
)

REM Launch the application
python dpa-image-toolkit.py

if %errorlevel% neq 0 (
    echo.
    echo ================================================================
    echo ERROR: Failed to start DPA Image Toolkit
    echo ================================================================
    echo.
    echo If you see an error about missing dependencies, follow these steps:
    echo   1. Open Command Prompt or PowerShell
    echo   2. Run: pip install customtkinter pillow opencv-python numpy
    echo   3. Try launching again
    echo.
    echo If problems persist, contact support with the error message above.
    echo.
    pause
)

endlocal
