@echo off
chcp 65001 >nul
REM Start Electron Frontend App
REM Note: This script does not activate conda env, uses system default Node.js

echo ========================================
echo Mold Surface Inspector System
echo Electron 3D Visualization Frontend
echo ========================================
echo.

REM Switch to electron directory
cd /d "%~dp0electron"

REM Check if npm is available
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [Error] npm not found, refreshing environment variables...
    echo.
    REM Refresh environment variables
    for /f "tokens=*" %%i in ('powershell -Command "[System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')"') do set PATH=%%i
)

REM Start Electron App
echo Starting Electron App...
echo.
echo Tips:
echo 1. Ensure Modbus Simulator is running (run start_modbus_sim.bat)
echo 2. In the app interface, enter PLC IP: 127.0.0.1, Port: 502
echo 3. Click "Connect PLC" button to start measurement
echo.
echo ========================================
echo.

npm start

REM If startup fails, show error message
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Error] Electron startup failed
    echo.
    echo Possible reasons:
    echo 1. Node.js is not installed or not in PATH
    echo 2. Dependencies not installed, please run: npm install
    echo.
    pause
)
