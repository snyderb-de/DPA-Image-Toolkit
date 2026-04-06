@echo off
REM DPA Image Toolkit Launcher
REM This launcher can live anywhere (for example, on the Desktop).
REM It prefers the deployed app in %USERPROFILE%\Scripts\dpa-img-tk\
REM and falls back to a local app copy beside this batch file.

setlocal enabledelayedexpansion

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
set "USER_SCRIPTS=%USERPROFILE%\Scripts"
set "DEPLOY_ROOT=%USER_SCRIPTS%\dpa-img-tk"
set "TARGET_PY=%DEPLOY_ROOT%\dpa-image-toolkit.py"
set "LOCAL_PY=%SCRIPT_DIR%dpa-image-toolkit.py"
set "REQUIREMENTS_FILE=%DEPLOY_ROOT%\requirements.txt"

if exist "%TARGET_PY%" (
    set "APP_LAUNCHER=%TARGET_PY%"
) else if exist "%LOCAL_PY%" (
    set "APP_LAUNCHER=%LOCAL_PY%"
    set "REQUIREMENTS_FILE=%SCRIPT_DIR%requirements.txt"
) else (
    echo.
    echo ================================================================
    echo ERROR: Could not find dpa-image-toolkit.py
    echo ================================================================
    echo.
    echo Expected deployed app location:
    echo   %TARGET_PY%
    echo.
    echo Or local fallback location:
    echo   %LOCAL_PY%
    echo.
    echo Copy the deploy bundle into:
    echo   %USER_SCRIPTS%
    echo.
    pause
    exit /b 1
)

set "PYTHON_CMD="
py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py -3"
) else (
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD (
    echo.
    echo ================================================================
    echo ERROR: Python is not installed or not in your PATH
    echo ================================================================
    echo.
    echo To fix this:
    echo   1. Install Python from https://www.python.org/downloads/
    echo   2. Make sure Python or py.exe is available in PATH
    echo   3. Restart your computer
    echo.
    pause
    exit /b 1
)

REM Launch the application
%PYTHON_CMD% "%APP_LAUNCHER%"

if %errorlevel% neq 0 (
    echo.
    echo ================================================================
    echo ERROR: Failed to start DPA Image Toolkit
    echo ================================================================
    echo.
    echo If you see an error about missing dependencies, follow these steps:
    echo   1. Open Command Prompt or PowerShell
    echo   2. Run: %PYTHON_CMD% -m pip install -r "%REQUIREMENTS_FILE%"
    echo   3. Try launching again
    echo.
    echo If problems persist, contact support with the error message above.
    echo.
    pause
)

endlocal
