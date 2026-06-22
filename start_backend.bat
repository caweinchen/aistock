@echo off
setlocal

set PORT=8000
set VENV_DIR=.venv

echo ============================================
echo          AIStock Backend Start Script
echo ============================================
echo.

echo [1/3] Checking port %PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    echo Port %PORT% is used by PID=%%a, killing...
    taskkill /F /PID %%a >nul 2>&1
)
echo Port check done

echo.
echo [2/3] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

echo.
echo [3/3] Starting backend server...
echo Server will run on http://localhost:%PORT%
echo Press Ctrl+C to stop
echo.

python -m uvicorn backend.app.main:app --host 0.0.0.0 --port %PORT%

endlocal