@echo off
setlocal

set PORT=8081
set DOTS_SLASH_DIR=%USERPROFILE%\AppData\Local\.dotslash

echo ============================================
echo          AIStock Frontend Start Script
echo ============================================
echo.

REM Create dotslash directory
cd /d "%~dp0"

echo [1/4] Checking directories...
mkdir "%DOTS_SLASH_DIR%" >nul 2>&1
echo Directory check done

REM Check if port is in use
echo [2/4] Checking port %PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    echo Port %PORT% is used by PID=%%a, killing...
    taskkill /F /PID %%a >nul 2>&1
)
echo Port check done

echo.
echo [3/4] Setting environment variables...
set DOTS_SLASH_STORE_DIR=%DOTS_SLASH_DIR%
echo Environment setup done

echo.
echo [4/4] Starting frontend server...
echo Server will run on http://localhost:%PORT%
echo Press Ctrl+C to stop
echo.

npm run web -- --port %PORT%

endlocal