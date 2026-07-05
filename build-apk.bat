@echo off
echo ============================================
echo   AIStock Android APK Build Script
echo ============================================
echo.

set ANDROID_HOME=d:\CodexCode\AIStock-new\android-sdk
set ANDROID_SDK_ROOT=d:\CodexCode\AIStock-new\android-sdk
set JAVA_HOME=d:\CodexCode\AIStock-new\android-sdk\jdk17

echo [1/3] Setting environment variables...
echo   ANDROID_HOME=%ANDROID_HOME%
echo   JAVA_HOME=%JAVA_HOME%
echo.

echo [2/3] Building APK...
cd frontend\android
call gradlew.bat assembleRelease
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)
echo.

echo [3/3] Copying APK to project root...
copy /Y "app\build\outputs\apk\release\app-release.apk" "..\..\AIStock-release.apk"
echo.

echo ============================================
echo   BUILD SUCCESSFUL!
echo   APK: AIStock-release.apk
echo ============================================
pause