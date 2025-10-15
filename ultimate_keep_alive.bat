@echo off
REM ==================================================
REM 궁극의 감시 스크립트 - Ollama + 트레이더 3개
REM ==================================================
REM 사용자 요구: "ollama 항상 실행될 수 있게 삼중 안전장치 구현"
REM ==================================================

title 궁극의 감시견 - Ollama + 트레이더 3개

echo.
echo ======================================================================
echo   궁극의 감시견 시작
echo ======================================================================
echo   감시 대상 (4개):
echo   1. Ollama Server (포트 11434) - ETH/Self-improve용
echo   2. ETH Trader (llm_eth_trader_v4_3tier.py)
echo   3. KIS Trader (kis_llm_trader_v2_explosive.py)
echo   4. Manager Practice (unified_trader_manager 연습.py)
echo ======================================================================
echo   15초마다 프로세스 확인 후 죽으면 즉시 재시작
echo ======================================================================
echo.

set PYTHON=C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe
set ETH_SCRIPT=C:\Users\user\Documents\코드3\llm_eth_trader_v4_3tier.py
set KIS_SCRIPT=C:\Users\user\Documents\코드4\kis_llm_trader_v2_explosive.py
set MGR_SCRIPT=C:\Users\user\Documents\코드5\unified_trader_manager 연습.py

REM 초기 시작: Ollama 먼저 시작
echo [%TIME%] [초기화] Ollama 서버 시작...
start "Ollama Server" /MIN cmd /c ollama serve
timeout /t 5 /nobreak >nul

:LOOP
    echo [%TIME%] ========== 프로세스 확인 시작 ==========

    REM 1. Ollama Server 확인 (포트 11434 체크)
    netstat -ano | findstr ":11434" | findstr "LISTENING" >NUL
    if errorlevel 1 (
        echo [%TIME%] [CRITICAL] Ollama 서버 죽음! 즉시 재시작...
        taskkill /F /IM ollama.exe 2>NUL
        start "Ollama Server" /MIN cmd /c ollama serve
        timeout /t 5 /nobreak >nul
        echo [%TIME%] [OK] Ollama 서버 재시작 완료
    ) else (
        echo [%TIME%] [OK] Ollama 서버 정상 (포트 11434)
    )

    REM 2. ETH Trader 확인
    tasklist /FI "WINDOWTITLE eq ETH Trader*" 2>NUL | find "python.exe" >NUL
    if errorlevel 1 (
        echo [%TIME%] [ERROR] ETH Trader 죽음! 재시작 중...
        start "ETH Trader" /MIN "%PYTHON%" "%ETH_SCRIPT%"
        timeout /t 3 /nobreak >nul
    ) else (
        echo [%TIME%] [OK] ETH Trader 정상
    )

    REM 3. KIS Trader 확인
    tasklist /FI "WINDOWTITLE eq KIS Trader*" 2>NUL | find "python.exe" >NUL
    if errorlevel 1 (
        echo [%TIME%] [ERROR] KIS Trader 죽음! 재시작 중...
        start "KIS Trader" /MIN "%PYTHON%" "%KIS_SCRIPT%"
        timeout /t 3 /nobreak >nul
    ) else (
        echo [%TIME%] [OK] KIS Trader 정상
    )

    REM 4. Manager Practice 확인
    tasklist /FI "WINDOWTITLE eq Manager Practice*" 2>NUL | find "python.exe" >NUL
    if errorlevel 1 (
        echo [%TIME%] [ERROR] Manager Practice 죽음! 재시작 중...
        start "Manager Practice" /MIN "%PYTHON%" "%MGR_SCRIPT%"
        timeout /t 3 /nobreak >nul
    ) else (
        echo [%TIME%] [OK] Manager Practice 정상
    )

    echo [%TIME%] ========== 모든 프로세스 정상, 15초 후 재확인 ==========
    echo.
    timeout /t 15 /nobreak >nul

goto LOOP
