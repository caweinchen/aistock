@echo off
setlocal

set PORT=8000
set VENV_DIR=D:\CodexCode\AIStock-new\.venv
set BACKEND_DIR=backend

echo ============================================
echo          AIStock Backend Start Script
echo ============================================
echo.

echo [1/4] Checking and freeing port %PORT%...
set "PID_FOUND="
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    echo Port %PORT% is used by PID=%%a
    set "PID_FOUND=%%a"
    echo Killing process...
    taskkill /F /PID %%a >nul 2>&1
)
if defined PID_FOUND (
    echo Waiting for process to terminate...
    ping -n 3 127.0.0.1 >nul
) else (
    echo Port %PORT% is free
)
echo Port check done
echo.

echo [2/4] Activating virtual environment...
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
echo Press Ctrl+C to stop
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT% --reload

endlocal