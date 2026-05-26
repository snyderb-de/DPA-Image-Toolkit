@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "APP_DIR=%SCRIPT_DIR%"

if exist "%SCRIPT_DIR%dpa-img-tk\launch_web.py" (
    set "APP_DIR=%SCRIPT_DIR%dpa-img-tk\"
)

if exist "%USERPROFILE%\Scripts\dpa-img-tk\launch_web.py" (
    set "APP_DIR=%USERPROFILE%\Scripts\dpa-img-tk\"
)

if not exist "%APP_DIR%launch_web.py" (
    echo ERROR: Could not find launch_web.py
    echo Expected at: %APP_DIR%launch_web.py
    pause
    exit /b 1
)

where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py -3 "%APP_DIR%launch_web.py" %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
    python "%APP_DIR%launch_web.py" %*
    exit /b %ERRORLEVEL%
)

echo ERROR: Python 3 not found. Install Python 3 and try again.
pause
exit /b 1
