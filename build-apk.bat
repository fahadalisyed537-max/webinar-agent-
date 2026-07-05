@echo off
echo ================================================
echo MindBloom - Android APK Build Script
echo ================================================
echo.

:: Check for Node.js
where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed!
    echo Please install Node.js from: https://nodejs.org/
    echo After installing, restart this script.
    pause
    exit /b 1
)

echo [OK] Node.js found
node --version
echo.

:: Check for npm
where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] npm is not found!
    pause
    exit /b 1
)

echo [OK] npm found
npm --version
echo.

:: Install dependencies
echo [1/5] Installing dependencies...
call npm install
if %ERRORLEVEL% neq 0 (
    echo [ERROR] npm install failed
    pause
    exit /b 1
)
echo.

:: Initialize Capacitor if needed
if not exist "android" (
    echo [2/5] Adding Android platform...
    call npx cap add android
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to add Android platform
        pause
        exit /b 1
    )
) else (
    echo [2/5] Android platform already exists
)
echo.

:: Sync web assets
echo [3/5] Syncing web assets to Android...
call npx cap sync android
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Capacitor sync failed
    pause
    exit /b 1
)
echo.

:: Check for Android SDK
if defined ANDROID_HOME (
    echo [OK] Android SDK found at: %ANDROID_HOME%
) else (
    echo [WARNING] ANDROID_HOME not set
    echo Please set ANDROID_HOME environment variable
    echo Or open the project in Android Studio:
    echo   npx cap open android
    pause
    exit /b 1
)
echo.

:: Build debug APK
echo [4/5] Building debug APK...
cd android
call gradlew.bat assembleDebug
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Build failed!
    echo Try opening the project in Android Studio:
    echo   npx cap open android
    cd ..
    pause
    exit /b 1
)
cd ..
echo.

:: Success
echo ================================================
echo [SUCCESS] Build completed!
echo ================================================
echo.
echo Debug APK location:
echo   android\app\build\outputs\apk\debug\app-debug.apk
echo.
echo To build a release APK:
echo   cd android && gradlew.bat assembleRelease
echo.
pause
