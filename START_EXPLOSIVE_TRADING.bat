@echo off
echo ================================================================================
echo Explosive Trading Bot Manager
echo ================================================================================
echo.
echo ETH Bot: +4654%% compound return
echo KIS Bot: +2634%% annual return
echo.
echo Starting...
echo ================================================================================
echo.

cd /d "C:\Users\user\Documents\코드5"

python unified_explosive_trader_manager.py --auto

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start
    echo.
)

pause
