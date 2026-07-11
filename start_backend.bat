@echo off
setlocal

if not defined PORT set PORT=8000
if not defined DB_HOST set DB_HOST=192.168.31.93
if not defined DB_PORT set DB_PORT=3306
if not defined DB_USERNAME set DB_USERNAME=aistock
if not defined DB_PASSWORD set DB_PASSWORD=AI@stock!234
if not defined DB_NAME set DB_NAME=ai_stock
if not defined VENV_DIR set VENV_DIR=%USERPROFILE%\.codex\venvs\aistock-ordinary-user-mvp

set SCRIPT_DIR=%~dp0
set BACKEND_DIR=%SCRIPT_DIR%backend

echo ============================================
echo          AIStock Backend Start Script
echo ============================================
echo.

echo [1/4] Checking port %PORT%...
set "PID_FOUND="
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    echo Port %PORT% is used by PID=%%a
    set "PID_FOUND=%%a"
    echo Killing process PID=%%a...
    taskkill /F /PID %%a >nul 2>&1
)
if defined PID_FOUND (
    echo Waiting for killed process to release port...
    ping -n 3 127.0.0.1 >nul
    set "PID_STILL_FOUND="
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
        set "PID_STILL_FOUND=%%a"
    )
    if defined PID_STILL_FOUND (
        echo ERROR: Port %PORT% is still in use by PID=%PID_STILL_FOUND%
        pause
        exit /b 1
    )
) else (
    echo Port %PORT% is free
)
echo Port check done
echo.

echo [2/4] Activating virtual environment...
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found:
    echo %VENV_DIR%
    echo Create it first or set VENV_DIR to an existing environment.
    pause
    exit /b 1
)
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated
echo.

echo [3/4] Navigating to backend directory...
cd /d "%BACKEND_DIR%"
if errorlevel 1 (
    echo ERROR: Failed to enter backend directory
    pause
    exit /b 1
)
echo.

echo [4/4] Starting backend server...
echo Server will run on http://localhost:%PORT%
echo Database will use %DB_HOST%:%DB_PORT%/%DB_NAME%
echo Press Ctrl+C to stop
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT% --reload

endlocal
