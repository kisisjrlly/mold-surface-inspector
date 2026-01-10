@echo off
chcp 65001 >nul
setlocal enableextensions
REM One-click startup script
REM Starts Modbus Simulator and Electron App

echo ========================================
echo Mold Surface Inspector System
echo Dual Probe Detection - One Click Start
echo ========================================
echo.

echo Starting services...
echo.
echo 1. Starting Modbus Simulator...
start "Modbus Simulator" cmd /k "%~dp0start_modbus_sim.bat"

echo 2. Waiting 3 seconds...
timeout /t 3 /nobreak >nul

echo 3. Starting Electron App...
start "Electron App" cmd /k "%~dp0start_electron.bat"

echo.
echo ========================================
echo Startup Complete!
echo.
echo Two windows have been opened:
echo - Modbus Simulator (Background)
echo - Electron App (3D Interface)
echo.
echo Instructions:
echo 1. In Electron interface, set PLC IP: 127.0.0.1
echo 2. Click "Connect PLC"
echo 3. Click "Start" to scan
echo.
echo Press any key to close this window...
echo ========================================
pause >nul
