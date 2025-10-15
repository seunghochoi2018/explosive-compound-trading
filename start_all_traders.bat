@echo off
REM ==================================================
REM 모든 트레이더 시작 스크립트
REM ==================================================
REM 사용자 요구: "매니저 연습도" "이더하고 kis" "항상 실행되게"
REM ==================================================

echo.
echo ==========================================
echo   모든 트레이더 시작 중...
echo ==========================================
echo.

REM Python 경로
set PYTHON=C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe

REM 1. ETH Trader
echo [1/3] ETH 트레이더 시작...
start "ETH Trader" /MIN "%PYTHON%" "C:\Users\user\Documents\코드3\llm_eth_trader_v4_3tier.py"
timeout /t 3 >nul

REM 2. KIS Trader
echo [2/3] KIS 트레이더 시작...
start "KIS Trader" /MIN "%PYTHON%" "C:\Users\user\Documents\코드4\kis_llm_trader_v2_explosive.py"
timeout /t 3 >nul

REM 3. Manager (연습)
echo [3/3] 통합매니저 (연습) 시작...
start "Manager Practice" /MIN "%PYTHON%" "C:\Users\user\Documents\코드5\unified_trader_manager 연습.py"
timeout /t 3 >nul

echo.
echo ==========================================
echo   모든 트레이더 시작 완료!
echo ==========================================
echo.
echo 닫기 전에 tasklist로 확인하세요.
echo.
pause
