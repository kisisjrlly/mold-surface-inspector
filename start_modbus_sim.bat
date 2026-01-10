@echo off
chcp 65001 >nul
REM Start Modbus Simulation Server
REM Dual Probe Detection Device Simulation

echo ========================================
echo Mold Surface Inspector System
echo Dual Probe Modbus Simulation Server
echo ========================================
echo.

REM Activate conda environment
call conda activate inspector

REM Start simulation server
echo Starting Modbus Simulation Server (Port 502)...
echo.
python modbus_sim_server.py

pause
